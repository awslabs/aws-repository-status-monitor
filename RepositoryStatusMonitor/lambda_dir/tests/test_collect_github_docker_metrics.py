import json
from unittest.mock import Mock, call, patch

import boto3
from moto import mock_secretsmanager

from lambda_dir import collect_github_docker_metrics as github_docker


@patch('lambda_dir.collect_github_docker_metrics.hh.request_handler')
def test_retrieve_unpaginated_metrics_good_response_no_param(mock_get):
    mock_get.return_value = True, {'test-message': 'test'}, {}
    mock_headers = {'test-headers': 'test'}
    mock_url = 'test-url/'
    mock_repo_name = 'test-repo-name'

    data = github_docker.retrieve_unpaginated_metrics(mock_url, mock_repo_name, mock_headers)

    mock_get.assert_called_once_with(headers=mock_headers, url=mock_url + mock_repo_name)
    assert data == {'test-message': 'test'}


@patch('lambda_dir.collect_github_docker_metrics.hh.request_handler')
def test_retrieve_unpaginated_metrics_good_response_with_param(mock_get):
    mock_get.return_value = True, {'test-message': 'test'}, {}
    mock_headers = {'test-headers': 'test'}
    mock_url = 'test-url/'
    mock_repo_name = 'test-repo-name'
    mock_param = 'test-param'

    data = github_docker.retrieve_unpaginated_metrics(mock_url, mock_repo_name, mock_headers, mock_param)

    expected_call_url = mock_url + mock_repo_name + '/' + mock_param
    mock_get.assert_called_once_with(headers=mock_headers, url=expected_call_url)
    assert data == {'test-message': 'test'}


@patch('lambda_dir.collect_github_docker_metrics.hh.request_handler')
def test_retrieve_unpaginated_metrics_bad_response(mock_get):
    mock_get.return_value = False, {'test-message': 'test'}, {}
    mock_headers = {'test-headers': 'test'}
    mock_url = 'test-url/'
    mock_repo_name = 'test-repo-name'

    data = github_docker.retrieve_unpaginated_metrics(mock_url, mock_repo_name, mock_headers)

    assert not data


@patch('lambda_dir.collect_github_docker_metrics.hh.request_handler')
def test_retrieve_unpaginated_metrics_empty_response(mock_get):
    mock_get.return_value = True, {}, {}
    mock_headers = {'test-headers': 'test'}
    mock_url = 'test-url/'
    mock_repo_name = 'test-repo-name'

    data = github_docker.retrieve_unpaginated_metrics(mock_url, mock_repo_name, mock_headers)

    assert not data


@patch('lambda_dir.collect_github_docker_metrics.hh.request_handler')
@patch('lambda_dir.collect_github_docker_metrics.hh.handle_pagination')
def test_retrieve_paginated_metrics_good_response(mock_paginate, mock_get):
    mock_data = {'test-pgn-1': 'test-pgn-1', 'test-pgn-2': 'test-pgn-2'}
    mock_paginate.return_value = True, mock_data
    mock_get.return_value = True, mock_data, {}
    mock_headers = {'test-headers': 'test'}
    mock_url = 'test-url/'
    mock_repo_name = 'test-repo-name'
    mock_metrics_to_retrieve = {'test-metric': 'test-metric-url-param'}
    mock_http_fields = {'page': 1, 'per_page': 100}
    data = github_docker.retrieve_paginated_metrics(mock_url, mock_repo_name, mock_metrics_to_retrieve, mock_headers)

    expected_call_url = mock_url + mock_repo_name + '/test-metric-url-param'
    mock_get.assert_called_once_with(expected_call_url, headers=mock_headers, http_fields=mock_http_fields)
    mock_paginate.assert_called_once_with(expected_call_url, mock_data, {}, mock_http_fields,
                                          request_headers=mock_headers)
    assert data == {'test-metric': 2}


@patch('lambda_dir.collect_github_docker_metrics.hh.request_handler')
@patch('lambda_dir.collect_github_docker_metrics.hh.handle_pagination')
def test_retrieve_paginated_metrics_good_response_bad_pagination(mock_paginate, mock_get):
    mock_data = {'test-pgn-1': 'test-pgn-1', 'test-pgn-2': 'test-pgn-2'}
    mock_paginate.return_value = False, mock_data
    mock_get.return_value = True, mock_data, {}
    mock_headers = {'test-headers': 'test'}
    mock_url = 'test-url/'
    mock_repo_name = 'test-repo-name'
    mock_metrics_to_retrieve = {'test-metric': 'test-metric-url-param'}
    mock_http_fields = {'page': 1, 'per_page': 100}
    data = github_docker.retrieve_paginated_metrics(mock_url, mock_repo_name, mock_metrics_to_retrieve, mock_headers)

    expected_call_url = mock_url + mock_repo_name + '/test-metric-url-param'
    mock_get.assert_called_once_with(expected_call_url, headers=mock_headers, http_fields=mock_http_fields)
    mock_paginate.assert_called_once_with(expected_call_url, mock_data, {}, mock_http_fields,
                                          request_headers=mock_headers)
    assert data == {'test-metric': 2}


@patch('lambda_dir.collect_github_docker_metrics.hh.request_handler')
@patch('lambda_dir.collect_github_docker_metrics.hh.handle_pagination')
def test_retrieve_paginated_metrics_bad_response(mock_paginate, mock_get, capfd):
    mock_data = {'test-metric-param': 'test-metric-value'}
    mock_get.return_value = False, mock_data, {}
    mock_headers = {'test-headers': 'test'}
    mock_url = 'test-url/'
    mock_repo_name = 'test-repo-name'
    mock_metrics_to_retrieve = {'test-metric': 'test-metric-url-param'}
    mock_http_fields = {'page': 1, 'per_page': 100}
    data = github_docker.retrieve_paginated_metrics(mock_url, mock_repo_name, mock_metrics_to_retrieve, mock_headers)

    expected_call_url = mock_url + mock_repo_name + '/test-metric-url-param'
    mock_get.assert_called_once_with(expected_call_url, headers=mock_headers, http_fields=mock_http_fields)
    mock_paginate.assert_not_called()

    out, err = capfd.readouterr()
    assert not data
    assert 'Could not retrieve requested data test-metric for repository test-repo-name' in out


def test_verify_and_retrieve_metric_data_no_nested_params():
    mock_metrics_to_retrieve_sorted_by_url = {'test-url': {'test-metric-name': 'test-metric-param'}}
    mock_response_data_sorted_by_url = {'test-url': {'test-metric-param': 0}}
    mock_repo_name = 'test-repo-name'

    metric_data_by_field, text_data_by_field = github_docker.verify_and_retrieve_metric_data(
        mock_metrics_to_retrieve_sorted_by_url, mock_response_data_sorted_by_url, mock_repo_name)
    assert metric_data_by_field == {'test-metric-name': 0}
    assert not text_data_by_field


def test_verify_and_retrieve_metric_data_nested_params():
    mock_metrics_to_retrieve_sorted_by_url = {'test-url': {'test-metric-name': 'nest*test-metric-param'}}
    mock_response_data_sorted_by_url = {'test-url': {'nest': {'test-metric-param': 0}}}
    mock_repo_name = 'test-repo-name'

    metric_data_by_field, text_data_by_field = github_docker.verify_and_retrieve_metric_data(
        mock_metrics_to_retrieve_sorted_by_url, mock_response_data_sorted_by_url, mock_repo_name)
    assert metric_data_by_field == {'test-metric-name': 0}
    assert not text_data_by_field


def test_verify_and_retrieve_metric_data_nested_params_list_and_dict():
    mock_metrics_to_retrieve_sorted_by_url = {'test-url': {'test-metric-name': 'nest*0*test-metric-param'}}
    mock_response_data_sorted_by_url = {'test-url': {'nest': [{'test-metric-param': 0}]}}
    mock_repo_name = 'test-repo-name'

    metric_data_by_field, text_data_by_field = github_docker.verify_and_retrieve_metric_data(
        mock_metrics_to_retrieve_sorted_by_url, mock_response_data_sorted_by_url, mock_repo_name)
    assert metric_data_by_field == {'test-metric-name': 0}
    assert not text_data_by_field


def test_verify_and_retrieve_metric_data_text_data():
    mock_metrics_to_retrieve_sorted_by_url = {
        'test-url': {'test-metric-name': 'test-metric-param', 'test-text-name': 'test-text-param'}}
    mock_response_data_sorted_by_url = {'test-url': {'test-metric-param': 0, 'test-text-param': 'test-data'}}
    mock_repo_name = 'test-repo-name'

    metric_data_by_field, text_data_by_field = github_docker.verify_and_retrieve_metric_data(
        mock_metrics_to_retrieve_sorted_by_url, mock_response_data_sorted_by_url, mock_repo_name)
    assert metric_data_by_field == {'test-metric-name': 0}
    assert text_data_by_field == {'test-text-name': 'test-data'}


def test_verify_and_retrieve_metric_data_bad_param_for_dict(capfd):
    mock_metrics_to_retrieve_sorted_by_url = {
        'test-url': {'test-metric-name': 'test-metric-param', 'test-text-name': '0*test-text-param'}}
    mock_response_data_sorted_by_url = {'test-url': {'test-metric-param': 0, 'test-text-param': 'test-data'}}
    mock_repo_name = 'test-repo-name'

    metric_data_by_field, text_data_by_field = github_docker.verify_and_retrieve_metric_data(
        mock_metrics_to_retrieve_sorted_by_url, mock_response_data_sorted_by_url, mock_repo_name)
    assert metric_data_by_field == {'test-metric-name': 0}
    assert not text_data_by_field
    assert 'test-text-name requested but not found for repository test-repo-name' in capfd.readouterr()[0]


def test_verify_and_retrieve_metric_data_no_param_in_param(capfd):
    mock_metrics_to_retrieve_sorted_by_url = {'test-url': {'test-metric-name': 'no-param-test'}}
    mock_response_data_sorted_by_url = {'test-url': {'no-param-test-data': 0}}
    mock_repo_name = 'test-repo-name'

    metric_data_by_field, text_data_by_field = github_docker.verify_and_retrieve_metric_data(
        mock_metrics_to_retrieve_sorted_by_url, mock_response_data_sorted_by_url, mock_repo_name)
    assert metric_data_by_field == {'test-metric-name': {'no-param-test-data': 0}}
    assert not text_data_by_field


def test_verify_and_retrieve_metric_data_bad_param_for_list(capfd):
    mock_metrics_to_retrieve_sorted_by_url = {'test-url': {'test-metric-name': 'test-metric-param'}}
    mock_response_data_sorted_by_url = {'test-url': [{'test-metric-param': 0}]}
    mock_repo_name = 'test-repo-name'

    metric_data_by_field, text_data_by_field = github_docker.verify_and_retrieve_metric_data(
        mock_metrics_to_retrieve_sorted_by_url, mock_response_data_sorted_by_url, mock_repo_name)
    assert not metric_data_by_field
    assert not text_data_by_field
    assert 'test-metric-name requested but not found for repository test-repo-name' in capfd.readouterr()[0]


def test_verify_and_retrieve_metric_data_too_many_nested_params(capfd):
    mock_metrics_to_retrieve_sorted_by_url = {'test-url': {'test-metric-name': 'test-metric-param*0'}}
    mock_response_data_sorted_by_url = {'test-url': {'test-metric-param': 0}}
    mock_repo_name = 'test-repo-name'

    metric_data_by_field, text_data_by_field = github_docker.verify_and_retrieve_metric_data(
        mock_metrics_to_retrieve_sorted_by_url, mock_response_data_sorted_by_url, mock_repo_name)
    assert not metric_data_by_field
    assert not text_data_by_field
    assert 'test-metric-name requested but not found for repository test-repo-name' in capfd.readouterr()[0]


def test_verify_and_retrieve_metric_data_no_data_for_url(capfd):
    mock_metrics_to_retrieve_sorted_by_url = {'test-url': {'test-metric-name': 'test-metric-param'}}
    mock_response_data_sorted_by_url = {'test-url-2': {'test-metric-param': 0}}
    mock_repo_name = 'test-repo-name'

    metric_data_by_field, text_data_by_field = github_docker.verify_and_retrieve_metric_data(
        mock_metrics_to_retrieve_sorted_by_url, mock_response_data_sorted_by_url, mock_repo_name)
    assert not metric_data_by_field
    assert not text_data_by_field
    assert 'No data for requested url parameter: test-url' in capfd.readouterr()[0]


def test_process_fields_no_slash_param_specified(monkeypatch):
    mock_name = 'test-name'
    monkeypatch.setenv(mock_name, '{"test-field":"test","test-field-2":"test-2"}')

    fields, param_name_mapping = github_docker.process_fields(mock_name)
    assert fields == {'None': {'test-field': 'test', 'test-field-2': 'test-2'}}
    assert param_name_mapping == {'test': 'test-field', 'test-2': 'test-field-2'}


def test_process_fields_with_slash_param_specified(monkeypatch):
    mock_name = 'test-name'
    monkeypatch.setenv(mock_name, '{"test-field":"test/1"}')

    fields, param_name_mapping = github_docker.process_fields(mock_name)
    assert fields == {'test': {'test-field': '1'}}
    assert param_name_mapping == {'test/1': 'test-field'}


def test_process_fields_with_slash_param_not_specified(monkeypatch):
    mock_name = 'test-name'
    monkeypatch.setenv(mock_name, '{"test-field":"test/"}')

    fields, param_name_mapping = github_docker.process_fields(mock_name)
    assert fields == {'test': {'test-field': 'no-param test'}}
    assert param_name_mapping == {'test': 'test-field'}


@mock_secretsmanager
@patch('lambda_dir.collect_github_docker_metrics.sort_metrics_by_widget')
@patch('lambda_dir.collect_github_docker_metrics.retrieve_paginated_metrics')
@patch('lambda_dir.collect_github_docker_metrics.verify_and_retrieve_metric_data')
@patch('lambda_dir.collect_github_docker_metrics.retrieve_unpaginated_metrics')
@patch('lambda_dir.collect_github_docker_metrics.process_fields')
def test_aggregate_metrics(mock_process, mock_unpgn, mock_verify, mock_pgn, mock_sort, capfd, monkeypatch,
                           aws_credentials):
    monkeypatch.setenv('docker_bool', 'y')
    monkeypatch.setenv('user_agent_header', 'test-user-agent-header')
    repo_name = 'test-repo-name'

    mock_process.side_effect = lambda name: ({'test-' + name: {'test-key': 'test-val'}}, {'test-name': 'test-param'})
    unpgn_metric = {'test-github-unpgn': 0}
    mock_unpgn.return_value = unpgn_metric
    mock_verify.side_effect = [({'test-github-unpgn': 0}, {}), ({}, {'test-docker': 'hello'})]
    mock_pgn.return_value = {'test-github-pgn': 12}
    mock_sort.side_effect = lambda metric, text, param_to_name: print('Requested metric data:', metric,
                                                                      '\nRequested text data:', text)

    with mock_secretsmanager():
        boto3.setup_default_session()
        boto3.client('secretsmanager').create_secret(
            Name='github_auth_token',
            SecretString='1234'
        )
        github_docker.aggregate_metrics('test-owner', repo_name)
        out, err = capfd.readouterr()
        assert "Requested metric data: {'test-github-unpgn': 0, 'test-github-pgn': 12}" in out
        assert "Requested text data: {'test-docker': 'hello'}" in out


@mock_secretsmanager
@patch('lambda_dir.collect_github_docker_metrics.sort_metrics_by_widget')
@patch('lambda_dir.collect_github_docker_metrics.retrieve_paginated_metrics')
@patch('lambda_dir.collect_github_docker_metrics.verify_and_retrieve_metric_data')
@patch('lambda_dir.collect_github_docker_metrics.retrieve_unpaginated_metrics')
@patch('lambda_dir.collect_github_docker_metrics.process_fields')
def test_aggregate_metrics_no_docker(mock_process, mock_unpgn, mock_verify, mock_pgn, mock_sort, capfd, monkeypatch,
                                     aws_credentials):
    monkeypatch.setenv('docker_bool', 'n')
    monkeypatch.setenv('user_agent_header', 'test-user-agent-header')
    repo_name = 'test-repo-name'

    mock_process.side_effect = lambda name: (
    {'test-' + name: {'test-key': 'test-val'}}, {'test-name-2': 'test-param-2'})
    unpgn_metric = {'test-github-unpgn': 0}
    mock_unpgn.return_value = unpgn_metric
    mock_verify.side_effect = [({'test-github-unpgn': 0}, {}), ({}, {'test-docker': 'hello'})]
    mock_pgn.return_value = {'test-github-pgn': 12}
    mock_sort.side_effect = lambda metric, text, param_to_name: print('Requested metric data:', metric,
                                                                      '\nRequested text data:', text)

    with mock_secretsmanager():
        boto3.setup_default_session()
        boto3.client('secretsmanager').create_secret(
            Name='github_auth_token',
            SecretString='1234'
        )
        github_docker.aggregate_metrics('test-owner', repo_name)
        out, err = capfd.readouterr()
        assert "Requested metric data: {'test-github-unpgn': 0, 'test-github-pgn': 12}" in out
        assert "Requested text data: {'test-docker': 'hello'}" not in out


@patch('lambda_dir.collect_github_docker_metrics.process_metrics')
def test_sort_metrics_by_widget_no_default(mock_process, monkeypatch):
    mock_process.side_effect = lambda sorted_metrics, param_to_name: sorted_metrics
    widgets = {'test-widget': {'dashboard_level': 'main', 'type': 'metric', 'metrics': ['test-metric-param']}}
    monkeypatch.setenv('widgets', json.dumps(widgets))
    monkeypatch.setenv('default_metric_widget_name', 'test-default-metric-name')
    monkeypatch.setenv('default_text_widget_name', 'test-default-text-name')

    mock_requested_metric_data = {'test-metric-name': 1}
    mock_param_to_name = {'test-metric-param': 'test-metric-name'}
    sorted_metrics = github_docker.sort_metrics_by_widget(mock_requested_metric_data, {}, mock_param_to_name)

    expected_sorted_metrics = {
        'test-widget': {
            'type': 'metric',
            'dashboard_level': 'main',
            'data': {'test-metric-name': 1}
        }
    }
    assert sorted_metrics == expected_sorted_metrics


@patch('lambda_dir.collect_github_docker_metrics.process_metrics')
def test_sort_metrics_by_widget_default_text(mock_process, monkeypatch):
    mock_process.side_effect = lambda sorted_metrics, param_to_name: sorted_metrics
    widgets = {'test-widget': {'dashboard_level': 'main', 'type': 'metric', 'metrics': ['test-metric-param']}}
    monkeypatch.setenv('widgets', json.dumps(widgets))
    monkeypatch.setenv('default_metric_widget_name', 'test-default-metric-name')
    monkeypatch.setenv('default_text_widget_name', 'test-default-text-name')

    mock_requested_metric_data = {'test-metric-name': 1}
    mock_requested_text_data = {'test-text-name': 'test-val'}
    mock_param_to_name = {'test-metric-param': 'test-metric-name', 'test-text-param': 'test-text-name'}
    sorted_metrics = github_docker.sort_metrics_by_widget(mock_requested_metric_data, mock_requested_text_data,
                                                          mock_param_to_name)

    expected_sorted_metrics = {
        'test-widget': {
            'type': 'metric',
            'dashboard_level': 'main',
            'data': {'test-metric-name': 1}
        },
        'test-default-text-name': {
            'type': 'text',
            'dashboard_level': 'main',
            'data': {'test-text-name': 'test-val'}
        }
    }

    assert sorted_metrics == expected_sorted_metrics


@patch('lambda_dir.collect_github_docker_metrics.process_metrics')
def test_sort_metrics_by_widget_default_text_left_over(mock_process, monkeypatch):
    mock_process.side_effect = lambda sorted_metrics, param_to_name: sorted_metrics
    widgets = {'test-widget': {'dashboard_level': 'main', 'type': 'metric', 'metrics': ['test-metric-param']}}
    monkeypatch.setenv('widgets', json.dumps(widgets))
    monkeypatch.setenv('default_metric_widget_name', 'test-default-metric-name')
    monkeypatch.setenv('default_text_widget_name', 'test-default-text-name')

    mock_requested_metric_data = {'test-metric-name': 1}
    mock_requested_text_data = {'test-text-name': 'test-val'}
    mock_param_to_name = {'test-text-param': 'test-text-name', 'test-metric-param': 'test-metric-name'}
    sorted_metrics = github_docker.sort_metrics_by_widget(mock_requested_metric_data, mock_requested_text_data,
                                                          mock_param_to_name)

    expected_sorted_metrics = {
        'test-widget': {
            'type': 'metric',
            'dashboard_level': 'main',
            'data': {'test-metric-name': 1}
        },
        'test-default-text-name': {
            'type': 'text',
            'dashboard_level': 'main',
            'data': {'test-text-name': 'test-val'}
        }
    }
    assert sorted_metrics == expected_sorted_metrics


@patch('lambda_dir.collect_github_docker_metrics.process_metrics')
def test_sort_metrics_by_widget_no_specified_widget(mock_process, monkeypatch):
    mock_process.side_effect = lambda sorted_metrics, param_to_name: sorted_metrics
    monkeypatch.setenv('widgets', json.dumps({}))
    monkeypatch.setenv('default_metric_widget_name', 'test-default-metric-name')
    monkeypatch.setenv('default_text_widget_name', 'test-default-text-name')

    mock_requested_metric_data = {'test-metric-name': 1}
    mock_requested_text_data = {'test-text-name': 'test-val'}
    mock_param_to_name = {'test-metric-param': 'test-metric-name', 'test-text-param': 'test-text-name'}
    sorted_metrics = github_docker.sort_metrics_by_widget(mock_requested_metric_data, mock_requested_text_data,
                                                          mock_param_to_name)

    expected_sorted_metrics = {
        'test-default-text-name': {
            'type': 'text',
            'dashboard_level': 'main',
            'data': {'test-text-name': 'test-val'}
        },
        'test-default-metric-name': {
            'type': 'metric',
            'dashboard_level': 'details',
            'data': {'test-metric-name': 1}
        }
    }
    assert sorted_metrics == expected_sorted_metrics


def test_process_metric_image_size():
    widget_to_process = {
        'test-widget-title': {'type': 'metric', 'dashboard_level': 'main', 'data': {'Test Image Size Metric': 1000000}}}
    param_to_name = {'tags/results*0*full_size': 'Test Image Size Metric'}
    processed_widgets = github_docker.process_metrics(widget_to_process, param_to_name)
    assert processed_widgets == {
        'test-widget-title': {'type': 'metric', 'dashboard_level': 'main', 'data': {'Test Image Size Metric': 1.0}}}


def test_process_metric_open_issues_no_prs():
    widget_to_process = {
        'test-widget-title': {'type': 'metric', 'dashboard_level': 'main', 'data': {'Test Open Issues Metric': 3}}}
    param_to_name = {'open_issues_count': 'Test Open Issues Metric'}
    processed_widgets = github_docker.process_metrics(widget_to_process, param_to_name)
    assert processed_widgets == {'test-widget-title': {'type': 'metric', 'dashboard_level': 'main',
                                                       'data': {'Open Issues and Pull Requests': 3}}}


def test_process_metric_open_issues_and_prs():
    widget_to_process = {'test-widget-title': {'type': 'metric', 'dashboard_level': 'main',
                                               'data': {'Test Open Issues Metric': 3, 'Test Open PRs Metric': 1}}}
    param_to_name = {'open_issues_count': 'Test Open Issues Metric', 'pulls': 'Test Open PRs Metric'}
    processed_widgets = github_docker.process_metrics(widget_to_process, param_to_name)
    assert processed_widgets == {'test-widget-title': {'type': 'metric', 'dashboard_level': 'main',
                                                       'data': {'Test Open Issues Metric': 2,
                                                                'Test Open PRs Metric': 1}}}


def test_process_metric_longest_inactive_issue():
    widget_to_process = {'test-widget-title': {'type': 'metric', 'dashboard_level': 'main',
                                               'data': {'Test Longest Inactive Issue Metric': '2020-08-20T02:39:42Z'}}}
    param_to_name = {'issues?sort=created&direction=asc/0*updated_at': 'Test Longest Inactive Issue Metric'}
    processed_widgets = github_docker.process_metrics(widget_to_process, param_to_name)
    assert processed_widgets == {'test-widget-title': {'type': 'metric', 'dashboard_level': 'main', 'data': {
        'Test Longest Inactive Issue Metric': 'August 20, 2020'}}}


def test_process_metric_top_referrers():
    top_referrers_data = [
        {
            'referrer': 'test-refer-1',
            'uniques': 5
        },
        {
            'referrer': 'test-refer-2',
            'uniques': 2
        }
    ]
    widget_to_process = {'test-widget-title': {'type': 'metric', 'dashboard_level': 'main',
                                               'data': {'Test Top Referrers': top_referrers_data}}}
    param_to_name = {'traffic/popular/referrers': 'Test Top Referrers'}
    processed_widgets = github_docker.process_metrics(widget_to_process, param_to_name)
    assert processed_widgets == {'Test Top Referrers': {'type': 'text', 'dashboard_level': 'details',
                                                        'data': {'test-refer-1': '5', 'test-refer-2': '2'}}}


def test_process_metric_languages():
    languages_data = {
        'language-1': 10,
        'language-2': 10
    }
    widget_to_process = {
        'test-widget-title': {'type': 'metric', 'dashboard_level': 'main', 'data': {'Test Languages': languages_data}}}
    param_to_name = {'languages': 'Test Languages'}
    processed_widgets = github_docker.process_metrics(widget_to_process, param_to_name)
    assert processed_widgets == {'Test Languages': {'type': 'text', 'dashboard_level': 'details',
                                                    'data': {'language-1': '50.0%', 'language-2': '50.0%'}}}


def test_process_metric_release_assets():
    release_asset_data = [
        {
            'name': 'asset-1',
            'download_count': 5
        },
        {
            'name': 'asset-2',
            'download_count': 2
        }
    ]
    widget_to_process = {'test-widget-title': {'type': 'metric', 'dashboard_level': 'main',
                                               'data': {'Test Release Assets': release_asset_data}}}
    param_to_name = {'releases/latest/assets': 'Test Release Assets'}
    processed_widgets = github_docker.process_metrics(widget_to_process, param_to_name)
    assert processed_widgets == {'Test Release Assets': {'type': 'text', 'dashboard_level': 'details',
                                                         'data': {'asset-1': '5', 'asset-2': '2', 'Total': '7'}}}
