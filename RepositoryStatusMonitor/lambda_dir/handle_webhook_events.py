import datetime
import math
import os

import boto3

import cloudwatch_interactions as cw_interactions
import http_handler as hh


def handle_webhook(payload: dict) -> dict:
    """Based on what type of webhook event is posted, calls separate handling functions

    :param payload: the payload of the POST request coming from the webhook
    :type payload: dict
    :returns: the widget representing the metric that the event is for or an empty dictionary if no widget is created
    :rtype: dict
    """
    dashboard_name_prefix = os.environ['dashboard_name_prefix']
    if 'issue' in payload.keys():
        return handle_issues(payload, dashboard_name_prefix)
    elif 'pull_request' in payload.keys():
        return handle_prs(payload, dashboard_name_prefix)
    elif 'release' in payload.keys():
        return handle_releases(payload, dashboard_name_prefix)
    elif 'pusher' in payload.keys():
        return handle_pushes(payload)
    return {}


def handle_prs(payload: dict, dashboard_name_prefix: str) -> dict:
    """Handles pull request webhook events

    :param payload: the payload of the POST request coming from the webhook
    :type payload: dict
    :param dashboard_name_prefix: the dashboard name prefix to use for the widget
    :type dashboard_name_prefix: str
    :returns: the widget representing the metric that the event is for or an empty dictionary if no widget is created
    :rtype: dict
    """
    labels = {
        'key': 'pull_request',
        'name': 'Pull Request Duration',
        'title': ' Pull Requests',
        'id': 'pullrequests'
    }
    if payload['action'] == 'closed':
        if payload['pull_request']['merged']:
            pr_merged_metric = cw_interactions.new_metric(payload['repository']['name'], 'PRs Merged', 1)
            cw_interactions.put_metrics_in_cloudwatch([pr_merged_metric])

        pr_closed_metric = cw_interactions.new_metric(payload['repository']['name'], 'PRs Closed', 1)
        cw_interactions.put_metrics_in_cloudwatch([pr_closed_metric])

        return create_issue_or_pr_widget(payload, labels, dashboard_name_prefix)

    if payload['action'] == 'opened':
        pr_opened_metric = cw_interactions.new_metric(payload['repository']['name'], 'PRs Opened', 1)
        cw_interactions.put_metrics_in_cloudwatch([pr_opened_metric])

    return {}


def handle_issues(payload: dict, dashboard_name_prefix: str) -> dict:
    """Handles issue webhook events

    :param payload: the payload of the POST request coming from the webhook
    :type payload: dict
    :param dashboard_name_prefix: the dashboard name prefix to use for the widget
    :type dashboard_name_prefix: str
    :returns: the widget representing the metric that the event is for or an empty dictionary if no widget is created
    :rtype: dict
    """
    labels = {
        'key': 'issue',
        'name': 'Issue Duration',
        'title': ' Issues',
        'id': 'issues'
    }
    if payload['action'] == 'closed':
        issue_closed_metric = cw_interactions.new_metric(payload['repository']['name'], 'Issues Closed', 1)
        cw_interactions.put_metrics_in_cloudwatch([issue_closed_metric])

        return create_issue_or_pr_widget(payload, labels, dashboard_name_prefix)

    if payload['action'] == 'opened':
        issue_opened_metric = cw_interactions.new_metric(payload['repository']['name'], 'Issues Opened', 1)
        cw_interactions.put_metrics_in_cloudwatch([issue_opened_metric])

    return {}


def create_issue_or_pr_widget(payload: dict, labels: dict, dashboard_name_prefix: str) -> dict:
    """Calculates the duration of an issue or PR and creates a widget representing the graph

    :param payload: the payload of the POST request coming from the webhook
    :type payload: dict
    :param labels: the payload key, metric name, and widget title for the webhook event
    :type labels: dict
    :param dashboard_name_prefix: the dashboard name prefix to use for the widget
    :type dashboard_name_prefix: str
    :returns: the widget representing the metric
    :rtype: dict
    """
    time_format = '%Y-%m-%dT%H:%M:%SZ'
    time_closed = datetime.datetime.strptime(payload[labels['key']]['closed_at'], time_format)
    time_created = datetime.datetime.strptime(payload[labels['key']]['created_at'], time_format)

    elapsed_time = time_closed - time_created
    repo_name = payload['repository']['name']
    data = {labels['name']: math.ceil(elapsed_time.total_seconds())}
    cw_metric = cw_interactions.create_metric_widget(repo_name, data, title=repo_name + labels['title'],
                                                     view='timeSeries', id_str=labels['id'], granularity='hours')
    widget = {
        dashboard_name_prefix + '-' + repo_name: [cw_metric]
    }
    return widget


def handle_releases(payload: dict, dashboard_name_prefix: str) -> dict:
    """Calculates the time between releases and creates a widget representing the graph

    :param payload: the payload of the POST request coming from the webhook
    :type payload: dict
    :param dashboard_name_prefix: the dashboard name prefix to use for the widget
    :type dashboard_name_prefix: str
    :returns: the widget representing the metric
    :rtype: dict
    """
    if payload['action'] == 'published':
        releases_metric = cw_interactions.new_metric(payload['repository']['name'], 'Releases Published', 1)
        cw_interactions.put_metrics_in_cloudwatch([releases_metric])

        token = boto3.client('secretsmanager').get_secret_value(SecretId='github_auth_token')['SecretString']
        headers = {
            'Authorization': 'token ' + token,
            'Accept': 'application/vnd.github.nebula-preview+json',
            'User-Agent': os.environ['user_agent_header']}
        repo_name = payload['repository']['name']
        url = 'https://api.github.com/repos/' + payload['repository']['owner']['login'] + '/' + repo_name + '/releases'

        success, http_data, response_headers = hh.request_handler(url, headers=headers)

        if success and len(http_data) > 1:
            last_release = http_data[1]

            time_format = '%Y-%m-%dT%H:%M:%SZ'
            time_end = datetime.datetime.strptime(payload['release']['published_at'], time_format)
            time_start = datetime.datetime.strptime(last_release['published_at'], time_format)
            elapsed_time = time_end - time_start

            data = {'Time Between Releases': math.ceil(elapsed_time.total_seconds())}
            widget = {
                dashboard_name_prefix + '-' + repo_name: [
                    cw_interactions.create_metric_widget(repo_name, data, title=repo_name + ' Releases',
                                                         view='timeSeries', id_str='releases', granularity='days')]
            }
            return widget
    return {}


def handle_pushes(payload: dict) -> dict:
    """Handles push webhook events

    :param payload: the payload of the POST request coming from the webhook
    :type payload: dict
    :returns: an empty widget because no widget is created for pushes
    :rtype: dict
    """
    if payload['ref'] == 'refs/heads/master':
        pushes_metric = cw_interactions.new_metric(payload['repository']['name'], 'Pushes to Master', 1)
        cw_interactions.put_metrics_in_cloudwatch([pushes_metric])
    return {}
