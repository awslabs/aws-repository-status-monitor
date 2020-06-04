from datetime import datetime
import json
import os

import boto3

import http_handler as hh


def aggregate_metrics(owner: str, repo_name: str) -> dict:
    """Aggregates all supported GitHub and Docker metrics for the specified repository

    :param owner: the owner of the repository
    :type owner: str
    :param repo_name: the repository name to collect metrics for
    :type repo_name: str
    :returns: the dictionary containing all the available, requested metrics, sorted by which widget they belong to
    :rtype: dict
    """

    github_fields_unpaginated, github_unpgn_param_name_mapping = process_fields('github_fields_unpaginated')
    github_fields_paginated, github_pgn_param_name_mapping = process_fields('github_fields_paginated')
    docker_fields, docker_param_name_mapping = process_fields('docker_fields')

    param_to_name = github_unpgn_param_name_mapping
    param_to_name.update(github_pgn_param_name_mapping)
    param_to_name.update(docker_param_name_mapping)

    github_headers = {
        'Authorization': "token " + boto3.client('secretsmanager').get_secret_value(
            SecretId="github_auth_token")['SecretString'],
        'Accept': 'application/vnd.github.nebula-preview+json',
        'User-Agent': os.environ['user_agent_header']
    }

    requested_metric_data = {}
    requested_text_data = {}

    github_url = 'https://api.github.com/repos/' + owner + '/'
    github_unpgn_data = {}

    for url_ending in github_fields_unpaginated.keys():
        request_param = None if url_ending == 'None' else url_ending
        github_unpgn_data[url_ending] = retrieve_unpaginated_metrics(github_url,
                                                                     repo_name,
                                                                     headers=github_headers,
                                                                     param=request_param)

    github_unpgn_requested_metrics, github_unpgn_text_data = verify_and_retrieve_metric_data(github_fields_unpaginated,
                                                                                             github_unpgn_data,
                                                                                             repo_name)
    github_pgn_requested_metrics = retrieve_paginated_metrics(github_url,
                                                              repo_name,
                                                              github_fields_paginated,
                                                              headers=github_headers)

    requested_metric_data.update(github_unpgn_requested_metrics)
    requested_metric_data.update(github_pgn_requested_metrics)
    requested_text_data.update(github_unpgn_text_data)

    include_docker = os.environ['docker_bool'] == 'y'
    if include_docker:
        docker_data = {}
        docker_url = 'https://hub.docker.com/v2/repositories/amazon/'

        for url_ending in docker_fields.keys():
            request_param = None if url_ending == 'None' else url_ending
            docker_data[url_ending] = retrieve_unpaginated_metrics(docker_url, repo_name, param=request_param)

        docker_requested_metrics, docker_requested_text_data = verify_and_retrieve_metric_data(docker_fields,
                                                                                               docker_data,
                                                                                               repo_name)

        requested_metric_data.update(docker_requested_metrics)
        requested_text_data.update(docker_requested_text_data)

    return sort_metrics_by_widget(requested_metric_data, requested_text_data, param_to_name)


def sort_metrics_by_widget(requested_metric_data: dict, requested_text_data: dict, param_to_name: dict) -> dict:
    """Sorts all metrics into a dictionary corresponding to the widget they belong to

    :param requested_metric_data: a dictionary of the numeric metrics
    :type requested_metric_data: dict
    :param requested_text_data: a dictionary of the text metrics
    :type requested_text_data: dict
    :returns: the dictionary containing all the available, requested metrics, sorted by which widget they belong to
    :rtype: dict
    """

    sorted_metrics = {}
    widgets = json.loads(os.environ['widgets'])
    for widget_title, widget_data in widgets.items():
        metric_values = {}
        dashboard_level = widget_data['dashboard_level'] if 'dashboard_level' in widget_data.keys() else 'details'

        for param in widget_data['metrics']:
            name = param_to_name[param]
            if name in requested_metric_data.keys():
                metric_values[name] = requested_metric_data[name]
                requested_metric_data.pop(name)
            elif name in requested_text_data.keys():
                metric_values[name] = requested_text_data[name]
                requested_text_data.pop(name)
            else:
                print('Requested metric ' + name + ' could not be retrieved.')

        if metric_values:
            sorted_metrics[widget_title] = {'type': widget_data['type'],
                                            'dashboard_level': dashboard_level,
                                            'data': metric_values}
        else:
            print('No valid metrics for widget ' + widget_title + '.')

    if requested_metric_data:
        default_metrics_data = sorted_metrics.get(os.environ['default_metric_widget_name'],
                                                  {'type': 'metric', 'dashboard_level': 'details', 'data': {}})
        default_metrics_data['data'].update(requested_metric_data)
        sorted_metrics[os.environ['default_metric_widget_name']] = default_metrics_data

    if requested_text_data:
        default_text_data = sorted_metrics.get(os.environ['default_text_widget_name'],
                                               {'type': 'text', 'dashboard_level': 'main', 'data': {}})
        default_text_data['data'].update(requested_text_data)
        sorted_metrics[os.environ['default_text_widget_name']] = default_text_data

    return process_metrics(sorted_metrics, param_to_name)


def retrieve_unpaginated_metrics(url: str, repo_name: str, headers=None, param=None):
    """Queries URL and returns unpaginated data

    :param url: the base URL to query
    :type url: str
    :param repo_name: the repository name to query
    :type repo_name: str
    :param headers: the HTTP headers to send with the request (default is None)
    :type headers: Optional[dict]
    :param param: the parameter to add to the URL (default is None)
    :type param: Optional[str]
    :returns: the data returned by the HTTP request 
    :rtype: dict or list
    """
    url += repo_name
    if param:
        url += '/' + param
    success, data, response_headers = hh.request_handler(headers=headers, url=url)
    if not success or data is None:
        return {}
    # can be list or dict depending on what API returns
    return data


def retrieve_paginated_metrics(url: str, repo_name: str, metrics_to_retrieve: dict, headers=None) -> dict:
    """Queries URL and if data is paginated, retrieves all further data from links provided in request headers

    :param url: the base URL to query
    :type url: str
    :param repo_name: the repository name to query
    :type repo_name: str
    :param metrics_to_retrieve: a mapping of the friendly metric names and the URL parameter that hosts the metric data (default is None)
    :type metrics_to_retrieve: dict
    :param headers: the HTTP headers to send with the request (default is None)
    :type headers: Optional[dict]
    :returns: a dictionary mapping the friendly metric name to the length of the dictionary of the paginated data
    :rtype: dict
    """
    requested_metric_data = {}
    http_fields = {'page': 1, 'per_page': 100}
    for metric_name, metric_url_ending in metrics_to_retrieve.items():
        temp_url = url + repo_name + '/' + metric_url_ending
        success, data, res_headers = hh.request_handler(temp_url, headers=headers, http_fields=http_fields)
        if success:
            pgn_success, pgn_data = hh.handle_pagination(temp_url, data, res_headers, http_fields,
                                                         request_headers=headers)
            requested_metric_data[metric_name] = len(pgn_data)
        else:
            print('Could not retrieve requested data ' + metric_name + ' for repository ' + repo_name)
    return requested_metric_data


def verify_and_retrieve_metric_data(metrics_to_retrieve_sorted_by_url: dict, response_data_sorted_by_url: dict,
                                    repo_name: str) -> tuple:
    """Verifies that the requested metrics exist in the data and returns a dictionary mapping the friendly names to the metric values

    :param metrics_to_retrieve_sorted_by_url: a dictionary of the requested metrics sorted by url
    :type metrics_to_retrieve_sorted_by_url: dict
    :param response_data_sorted_by_url: a dictionary of the response data from GitHub and DockerHub sorted by url
    :type response_data_sorted_by_url: dict
    :returns: the metrics that exist in the data and are numerical, the metrics that exist in the data and are text
    :rtype: tuple
    """
    metric_data_by_field = {}
    text_data_by_field = {}

    for metric_url_ending, metrics_to_retrieve in metrics_to_retrieve_sorted_by_url.items():
        if metric_url_ending not in response_data_sorted_by_url.keys():
            print('No data for requested url parameter:', metric_url_ending)
            continue

        response_data = response_data_sorted_by_url[metric_url_ending]

        for metric_name, metric_api_param in metrics_to_retrieve.items():
            nested_params = metric_api_param.split('*')
            valid = True

            data_set = response_data
            while len(nested_params) > 0:
                key = nested_params.pop(0)
                if 'no-param' in key:
                    break
                key = int(key) if key.isnumeric() else key

                valid_data_set = not isinstance(data_set, (list, dict))
                invalid_key_for_list = isinstance(data_set, list) and (isinstance(key, str) or len(data_set) <= key)
                invalid_key_for_dict = isinstance(data_set, dict) and (isinstance(key, int) or key not in data_set)
                if invalid_key_for_dict or invalid_key_for_list or valid_data_set:
                    print(metric_name, 'requested but not found for repository ' + repo_name)
                    valid = False
                    break

                data_set = data_set[key]

            if valid:
                if isinstance(data_set, str):
                    text_data_by_field[metric_name] = data_set
                else:
                    metric_data_by_field[metric_name] = data_set

    print("raw metric data for " + repo_name + ":")
    print(metric_data_by_field)
    print("raw text data for " + repo_name + ":")
    print(text_data_by_field)

    return metric_data_by_field, text_data_by_field


def process_fields(name: str) -> tuple:
    """Processes the environment variables that define the GitHub and Docker fields to retrieve metrics on

    :param name: the name of the environment variable to process
    :type name: str
    :returns: a dictionary of url endpoints mapped to a dictionary of metric names and API keys available at that endpoint,
              and the dictionary mapping all the api keys to the friendly names
    :rtype: tuple

    Example: If environment variables dict is {"github_fields_unpaginated": "Stars,stargazers_count;Latest GitHub Release,releases/0*name"},
    this method would be called like:
                fields = process_fields("github_fields_unpaginated")
            In this case, fields would be {"None: {"Stars": "stargazers_count"}, "releases": {"Latest GitHub Release": "0*name"}}
    """
    fields = {}
    param_name_mapping = {}
    for metric_name, metric_api_key in json.loads(os.environ[name]).items():
        if '/' in metric_api_key:
            # Split on last slash
            [url_ending, api_key] = metric_api_key.rsplit('/', 1)
        else:
            url_ending = 'None'
            api_key = metric_api_key

        if api_key == "":
            api_key = 'no-param ' + url_ending
            metric_api_key = url_ending

        fields_by_url = fields.get(url_ending, {})
        fields_by_url[metric_name] = api_key
        fields[url_ending] = fields_by_url
        param_name_mapping[metric_api_key] = metric_name

    if name != 'github_fields_paginated':
        return fields, param_name_mapping

    return fields['None'], param_name_mapping


def process_metrics(widgets: dict, param_to_name: dict) -> dict:
    """Alters any pre-specified widgets or metrics if they exist in the dictionary to make them more useful for the user
    Alterations include: changing unit of Docker Image Size from bytes to megabytes, creating a widget for release asset
    download counts, etc

    :param widgets: a dictionary mapping widget titles to widget data
    :type widgets: dict
    :param param_to_name: a dictionary mapping parameter fields to their human-friendly names
    :returns: the modified widgets dict
    :rtype: dict
    """
    image_size_key = param_to_name['tags/results*0*full_size'] if 'tags/results*0*full_size' in param_to_name.keys() else ""
    open_issues_key = param_to_name['open_issues_count'] if 'open_issues_count' in param_to_name.keys() else ""
    open_pr_key = param_to_name['pulls'] if 'pulls' in param_to_name.keys() else ""
    release_asset_key = param_to_name['releases/latest/assets'] if 'releases/latest/assets' in param_to_name.keys() else ""
    top_referrers_key = param_to_name['traffic/popular/referrers'] if 'traffic/popular/referrers' in param_to_name.keys() else ""
    longest_inactive_issue_key = param_to_name['issues?sort=created&direction=asc/0*updated_at'] if 'issues?sort=created&direction=asc/0*updated_at' in param_to_name.keys() else ""
    longest_inactive_pr_key = param_to_name['pulls?sort=updated/0*updated_at'] if 'pulls?sort=updated/0*updated_at' in param_to_name.keys() else ""
    languages_key = param_to_name['languages'] if 'languages' in param_to_name.keys() else ""

    release_asset_widget = {}
    top_referrers_widget = {}
    languages_widget = {}
    to_remove = []

    for widget_title, widget in widgets.items():
        metric_data = widget['data']

        # Changing unit from bytes to megabytes
        if image_size_key in metric_data.keys():
            metric_data[image_size_key] = metric_data[image_size_key] / 1000000

        # GitHub counts both open issues and open PRs in 'open_issues_count' metric
        # separating them here if possible, otherwise renaming
        if open_issues_key in metric_data.keys():
            if open_pr_key in metric_data.keys():
                metric_data[open_issues_key] = metric_data[open_issues_key] - metric_data[open_pr_key]
            else:
                metric_data['Open Issues and Pull Requests'] = metric_data[open_issues_key]
                metric_data.pop(open_issues_key)

        if longest_inactive_issue_key in metric_data.keys():
            updated_at = datetime.strptime(metric_data[longest_inactive_issue_key], '%Y-%m-%dT%H:%M:%SZ')
            metric_data[longest_inactive_issue_key] = updated_at.strftime('%B %d, %Y')

        if longest_inactive_pr_key in metric_data.keys():
            updated_at = datetime.strptime(metric_data[longest_inactive_pr_key], '%Y-%m-%dT%H:%M:%SZ')
            metric_data[longest_inactive_pr_key] = updated_at.strftime('%B %d, %Y')

        # Create new widget with top referrers to repo in last 14 days + how many unique visitors from each
        if top_referrers_key in metric_data.keys():
            top_referrers_widget = {'type': 'text',
                                    'dashboard_level': 'details',
                                    'data': {referrer['referrer']: str(referrer['uniques']) for referrer in
                                             metric_data[top_referrers_key]}}
            metric_data.pop(top_referrers_key)

        # Language names mapped to their usage %
        if languages_key in metric_data.keys():
            languages_widget = {'type': 'text', 'dashboard_level': 'details'}

            total_bytes = 0
            for num_bytes in metric_data[languages_key].values():
                total_bytes += num_bytes

            languages_widget['data'] = {language: str(round((num_bytes / total_bytes) * 100, 2)) + '%' for
                                        language, num_bytes in metric_data[languages_key].items()}
            metric_data.pop(languages_key)

        # Creating new widget with all release asset download counts
        if release_asset_key in metric_data.keys():
            release_asset_widget = {'type': 'text', 'dashboard_level': 'details'}
            release_asset_widget_data = {}

            total_download_count = 0
            for asset in metric_data[release_asset_key]:
                total_download_count += asset['download_count']
                release_asset_widget_data[asset['name']] = str(asset['download_count'])
            release_asset_widget_data['Total'] = str(total_download_count)
            release_asset_widget['data'] = release_asset_widget_data
            metric_data.pop(release_asset_key)

        if not metric_data:
            to_remove.append(widget_title)
        else:
            widget['data'] = metric_data

    for title in to_remove:
        widgets.pop(title)

    if top_referrers_widget:
        widgets[top_referrers_key] = top_referrers_widget

    if release_asset_widget:
        widgets[release_asset_key] = release_asset_widget

    if languages_widget:
        widgets[languages_key] = languages_widget

    return widgets
