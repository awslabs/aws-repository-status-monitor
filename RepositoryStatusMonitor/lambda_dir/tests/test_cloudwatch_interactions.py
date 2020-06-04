import json
import os
from unittest.mock import Mock, patch

import boto3
import botocore.session
from botocore.stub import Stubber
from moto import mock_cloudwatch

from lambda_dir import cloudwatch_interactions as cw


def test_new_metric_good_input():
    repo_name = 'repo-name'
    metric_name = 'metric-name'
    metric_value = 12
    metric = cw.new_metric(repo_name, metric_name, metric_value)

    metric_to_compare = {
        'MetricName': metric_name,
        'Dimensions': [
            {
                'Name': 'REPO_NAME',
                'Value': repo_name
            }
        ],
        'Unit': 'None',
        'Value': metric_value
    }
    assert metric == metric_to_compare


def test_new_metric_no_metric_name():
    repo_name = 'repo-name'
    metric_value = 12
    metric = cw.new_metric(repo_name, '', metric_value)
    assert not metric


def test_new_metric_no_repo_name():
    metric_name = 'metric-name'
    metric_value = 12
    metric = cw.new_metric('', metric_name, metric_value)
    assert not metric


def test_new_metric_metric_value_is_str_but_is_numeric():
    repo_name = 'repo-name'
    metric_name = 'metric-name'
    metric_value = '12'
    metric = cw.new_metric(repo_name, metric_name, metric_value)

    metric_to_compare = {
        'MetricName': metric_name,
        'Dimensions': [
            {
                'Name': 'REPO_NAME',
                'Value': repo_name
            }
        ],
        'Unit': 'None',
        'Value': float(metric_value)
    }
    assert metric == metric_to_compare


def test_new_metric_metric_value_is_str_and_is_not_numeric():
    repo_name = 'repo-name'
    metric_name = 'metric-name'
    metric_value = 'hello'
    metric = cw.new_metric(repo_name, metric_name, metric_value)
    assert not metric


def test_new_metric_metric_value_is_not_str_or_numeric():
    repo_name = 'repo-name'
    metric_name = 'metric-name'
    metric_value = []
    metric = cw.new_metric(repo_name, metric_name, metric_value)
    assert not metric


def test_new_metric_empty_metric_value():
    repo_name = 'repo-name'
    metric_name = 'metric-name'
    metric_value = ''
    metric = cw.new_metric(repo_name, metric_name, metric_value)
    assert not metric


def test_create_text_widget_good_input():
    title = 'repo-name Properties'
    text_data = {'test_key': 'test_val'}
    text_widget = cw.create_text_widget(text_data, title)

    text_widget_to_compare = {
        'type': 'text',
        'height': 4,
        'properties': {
            'markdown': '## repo-name Properties\n Name | Value \n ----|----- \ntest_key | test_val\n'
        }
    }
    assert text_widget == text_widget_to_compare


def test_create_text_widget_empty_title():
    title = ''
    text_data = {'test_key': 'test_val'}
    text_widget = cw.create_text_widget(text_data, title)
    assert not text_widget


def test_create_text_widget_missing_text_data():
    title = 'repo-name Properties'
    text_data = {}
    text_widget = cw.create_text_widget(text_data, title)
    assert not text_widget


def test_create_text_widget_bad_text_data():
    title = 'repo-name Properties'
    text_data = []
    text_widget = cw.create_text_widget(text_data, title)
    assert not text_widget


@mock_cloudwatch
def test_create_metric_widget_good_input_no_granularity(monkeypatch, aws_credentials):
    monkeypatch.setenv("namespace", "namespace")
    repo_name = 'repo-name'
    metric_data = {'test_val_2': 12}
    title = 'repo-name widget'
    metric_widget = cw.create_metric_widget(repo_name, metric_data, title=title)
    widget_metric_data = [['namespace', 'test_val_2', 'REPO_NAME', repo_name]]

    metric_widget_to_compare = {
        'type': 'metric',
        'width': 6,
        'height': 3,
        'properties': {
            'metrics': widget_metric_data,
            'view': 'singleValue',
            'period': 3600,
            'stat': 'Maximum',
            'region': 'us-west-2',
            'title': title
        }
    }

    assert metric_widget == metric_widget_to_compare


@mock_cloudwatch
def test_create_metric_widget_good_input_with_granularity_minutes(monkeypatch, aws_credentials):
    monkeypatch.setenv("namespace", "namespace")
    repo_name = 'repo-name'
    metric_data = {'test_val_2': 12000}
    title = 'repo-name widget'
    metric_widget = cw.create_metric_widget(repo_name, metric_data, title=title, id_str='test', granularity='minutes')
    widget_metric_data = [
        ['namespace', 'test_val_2', 'REPO_NAME', repo_name, {"id": 'test', "visible": False}],
        [{'expression': 'test/(60)', 'label': 'test_val_2 (in minutes)', "id": "testExpression"}]
    ]

    metric_widget_to_compare = {
        'type': 'metric',
        'width': 6,
        'height': 3,
        'properties': {
            'metrics': widget_metric_data,
            'view': 'singleValue',
            'period': 3600,
            'stat': 'Maximum',
            'region': 'us-west-2',
            'title': title
        }
    }

    assert metric_widget == metric_widget_to_compare


@mock_cloudwatch
def test_create_metric_widget_good_input_with_granularity_hours(monkeypatch, aws_credentials):
    monkeypatch.setenv("namespace", "namespace")
    repo_name = 'repo-name'
    metric_data = {'test_val_2': 12000}
    title = 'repo-name widget'
    metric_widget = cw.create_metric_widget(repo_name, metric_data, title=title, id_str='test', granularity='hours')
    widget_metric_data = [
        ['namespace', 'test_val_2', 'REPO_NAME', repo_name, {"id": 'test', "visible": False}],
        [{'expression': 'test/(3600)', 'label': 'test_val_2 (in hours)', "id": "testExpression"}]
    ]

    metric_widget_to_compare = {
        'type': 'metric',
        'width': 6,
        'height': 3,
        'properties': {
            'metrics': widget_metric_data,
            'view': 'singleValue',
            'period': 3600,
            'stat': 'Maximum',
            'region': 'us-west-2',
            'title': title
        }
    }

    assert metric_widget == metric_widget_to_compare


@mock_cloudwatch
def test_create_metric_widget_good_input_with_granularity_days(monkeypatch, aws_credentials):
    monkeypatch.setenv("namespace", "namespace")
    repo_name = 'repo-name'
    metric_data = {'test_val_2': 12000}
    title = 'repo-name widget'
    metric_widget = cw.create_metric_widget(repo_name, metric_data, title=title, id_str='test', granularity='days')
    widget_metric_data = [
        ['namespace', 'test_val_2', 'REPO_NAME', repo_name, {"id": 'test', "visible": False}],
        [{'expression': 'test/(3600*24)', 'label': 'test_val_2 (in days)', "id": "testExpression"}]
    ]

    metric_widget_to_compare = {
        'type': 'metric',
        'width': 6,
        'height': 3,
        'properties': {
            'metrics': widget_metric_data,
            'view': 'singleValue',
            'period': 3600,
            'stat': 'Maximum',
            'region': 'us-west-2',
            'title': title
        }
    }

    assert metric_widget == metric_widget_to_compare


@mock_cloudwatch
def test_create_metric_widget_with_invalid_granularity(monkeypatch, aws_credentials):
    monkeypatch.setenv("namespace", "namespace")
    repo_name = 'repo-name'
    metric_data = {'test_val_2': 12000}
    title = 'repo-name widget'
    metric_widget = cw.create_metric_widget(repo_name, metric_data, title=title, id_str='test', granularity='years')
    widget_metric_data = [
        ['namespace', 'test_val_2', 'REPO_NAME', repo_name]
    ]

    metric_widget_to_compare = {
        'type': 'metric',
        'width': 6,
        'height': 3,
        'properties': {
            'metrics': widget_metric_data,
            'view': 'singleValue',
            'period': 3600,
            'stat': 'Maximum',
            'region': 'us-west-2',
            'title': title
        }
    }

    assert metric_widget == metric_widget_to_compare


@mock_cloudwatch
def test_create_metric_widget_granularity_with_missing_id_str(monkeypatch, aws_credentials):
    monkeypatch.setenv("namespace", "namespace")
    repo_name = 'repo-name'
    metric_data = {'test_val_2': 12000}
    title = 'repo-name widget'
    metric_widget = cw.create_metric_widget(repo_name, metric_data, title=title, granularity='hours')
    widget_metric_data = [
        ['namespace', 'test_val_2', 'REPO_NAME', repo_name]
    ]

    metric_widget_to_compare = {
        'type': 'metric',
        'width': 6,
        'height': 3,
        'properties': {
            'metrics': widget_metric_data,
            'view': 'singleValue',
            'period': 3600,
            'stat': 'Maximum',
            'region': 'us-west-2',
            'title': title
        }
    }

    assert metric_widget == metric_widget_to_compare


@mock_cloudwatch
def test_create_metric_widget_granularity_with_empty_id_str(monkeypatch, aws_credentials):
    monkeypatch.setenv("namespace", "namespace")
    repo_name = 'repo-name'
    metric_data = {'test_val_2': 12000}
    title = 'repo-name widget'
    metric_widget = cw.create_metric_widget(repo_name, metric_data, title=title, id_str='', granularity='hours')
    widget_metric_data = [
        ['namespace', 'test_val_2', 'REPO_NAME', repo_name]
    ]

    metric_widget_to_compare = {
        'type': 'metric',
        'width': 6,
        'height': 3,
        'properties': {
            'metrics': widget_metric_data,
            'view': 'singleValue',
            'period': 3600,
            'stat': 'Maximum',
            'region': 'us-west-2',
            'title': title
        }
    }

    assert metric_widget == metric_widget_to_compare


@mock_cloudwatch
def test_create_metric_widget_with_missing_granularity(monkeypatch, aws_credentials):
    monkeypatch.setenv("namespace", "namespace")
    repo_name = 'repo-name'
    metric_data = {'test_val_2': 12000}
    title = 'repo-name widget'
    metric_widget = cw.create_metric_widget(repo_name, metric_data, title=title, id_str='test')
    widget_metric_data = [
        ['namespace', 'test_val_2', 'REPO_NAME', repo_name]
    ]

    metric_widget_to_compare = {
        'type': 'metric',
        'width': 6,
        'height': 3,
        'properties': {
            'metrics': widget_metric_data,
            'view': 'singleValue',
            'period': 3600,
            'stat': 'Maximum',
            'region': 'us-west-2',
            'title': title
        }
    }

    assert metric_widget == metric_widget_to_compare


@mock_cloudwatch
def test_create_metric_widget_empty_repo_name(monkeypatch, aws_credentials):
    monkeypatch.setenv("namespace", "namespace")
    metric_data = {'test_val_2': 12000}
    title = 'repo-name widget'
    metric_widget = cw.create_metric_widget('', metric_data, title=title)
    assert not metric_widget


@mock_cloudwatch
def test_create_metric_widget_empty_metric_data(monkeypatch, aws_credentials):
    monkeypatch.setenv("namespace", "namespace")
    repo_name = 'repo-name'
    metric_data = {'test_val_2': 12000}
    title = 'repo-name widget'
    metric_widget = cw.create_metric_widget(repo_name, {}, title=title)
    assert not metric_widget


@mock_cloudwatch
def test_create_metric_widget_verify_height_functionality(monkeypatch, aws_credentials):
    monkeypatch.setenv("namespace", "namespace")
    repo_name = 'repo-name'
    title = 'repo-name widget'

    metric_data_height_1 = {
        'test_val_1': 12000,
        'test_val_2': 12000,
        'test_val_3': 12000,
    }
    metric_widget_height_1 = cw.create_metric_widget(repo_name, metric_data_height_1, title=title)
    widget_metric_data_height_1 = [
        ['namespace', 'test_val_1', 'REPO_NAME', repo_name],
        ['namespace', 'test_val_2', 'REPO_NAME', repo_name],
        ['namespace', 'test_val_3', 'REPO_NAME', repo_name]
    ]
    metric_widget_to_compare_height_1 = {
        'type': 'metric',
        'width': 6,
        'height': 3,
        'properties': {
            'metrics': widget_metric_data_height_1,
            'view': 'singleValue',
            'period': 3600,
            'stat': 'Maximum',
            'region': 'us-west-2',
            'title': title
        }
    }

    metric_data_height_2 = {
        'test_val_1': 12000,
        'test_val_2': 12000,
        'test_val_3': 12000,
        'test_val_4': 12000
    }
    metric_widget_height_2 = cw.create_metric_widget(repo_name, metric_data_height_2, title=title)
    widget_metric_data_height_2 = [
        ['namespace', 'test_val_1', 'REPO_NAME', repo_name],
        ['namespace', 'test_val_2', 'REPO_NAME', repo_name],
        ['namespace', 'test_val_3', 'REPO_NAME', repo_name],
        ['namespace', 'test_val_4', 'REPO_NAME', repo_name]
    ]
    metric_widget_to_compare_height_2 = {
        'type': 'metric',
        'width': 6,
        'height': 6,
        'properties': {
            'metrics': widget_metric_data_height_2,
            'view': 'singleValue',
            'period': 3600,
            'stat': 'Maximum',
            'region': 'us-west-2',
            'title': title
        }
    }

    assert metric_widget_height_1 == metric_widget_to_compare_height_1
    assert metric_widget_height_2 == metric_widget_to_compare_height_2


@mock_cloudwatch
def test_create_or_update_dashboard_good_input_no_preexisting_dashboard(monkeypatch, capfd, aws_credentials):
    monkeypatch.setenv("dashboard_name", "dash-name")
    dashboard_widget_mapping = {
        'test-main-dash': [
            {
                'type': 'metric',
                'width': 6,
                'height': 6,
                'properties': {
                    'metrics': [
                        ['namespace', 'GitHub Stars', 'REPO_NAME', 'repo-name']
                    ],
                    'view': 'singleValue',
                    'period': 3600,
                    'stat': 'Maximum',
                    'region': os.environ['AWS_REGION'],
                    'title': 'dash-name Repository Status'
                }
            }
        ]
    }

    cw.create_or_update_dashboard(dashboard_widget_mapping)
    out, err = capfd.readouterr()
    assert 'Dashboard input invalid. Could not create dashboard.' not in out


@mock_cloudwatch
def test_create_or_update_dashboard_good_input_with_preexisting_dashboard(monkeypatch, capfd, aws_credentials):
    cloudwatch = boto3.client('cloudwatch')
    dashboard_name = 'dash-name'
    pre_existing_widgets = [
        {
            'type': 'text',
            'width': 6,
            'height': 6,
            'properties': {
                'markdown': 'hello'
            }
        }
    ]
    cloudwatch.put_dashboard(
        DashboardName=dashboard_name,
        DashboardBody=json.dumps({'widgets': pre_existing_widgets})
    )

    monkeypatch.setenv("dashboard_name", dashboard_name)
    dashboard_widget_mapping = {
        dashboard_name: [
            {
                'type': 'metric',
                'width': 6,
                'height': 6,
                'properties': {
                    'metrics': [
                        ['namespace', 'GitHub Stars', 'REPO_NAME', 'repo-name']
                    ],
                    'view': 'singleValue',
                    'period': 3600,
                    'stat': 'Maximum',
                    'region': os.environ['AWS_REGION'],
                    'title': dashboard_name + ' Repository Status'
                }
            }
        ]
    }
    cw.create_or_update_dashboard(dashboard_widget_mapping)
    out, err = capfd.readouterr()
    assert 'Dashboard input invalid. Could not create dashboard.' not in out

    updated_widgets = json.loads(cloudwatch.get_dashboard(DashboardName=dashboard_name)['DashboardBody'])['widgets']
    assert len(updated_widgets) == 2


@mock_cloudwatch
def test_create_or_update_dashboard_good_input_overwrite_same_widget(monkeypatch, capfd, aws_credentials):
    cloudwatch = boto3.client('cloudwatch')
    dashboard_name = 'dash-name'
    pre_existing_widgets = [
        {
            'type': 'metric',
            'width': 6,
            'height': 6,
            'properties': {
                'metrics': [
                    ['namespace', 'GitHub Stars', 'REPO_NAME', 'repo-name']
                ],
                'view': 'singleValue',
                'period': 3600,
                'stat': 'Maximum',
                'region': os.environ['AWS_REGION'],
                'title': dashboard_name + ' Repository Status'
            }
        }
    ]
    cloudwatch.put_dashboard(
        DashboardName=dashboard_name,
        DashboardBody=json.dumps({'widgets': pre_existing_widgets})
    )

    monkeypatch.setenv("dashboard_name", dashboard_name)
    dashboard_widget_mapping = {
        dashboard_name: [
            {
                'type': 'metric',
                'width': 6,
                'height': 6,
                'properties': {
                    'metrics': [
                        ['namespace', 'GitHub Stars', 'REPO_NAME', 'repo-name']
                    ],
                    'view': 'singleValue',
                    'period': 3600,
                    'stat': 'Maximum',
                    'region': os.environ['AWS_REGION'],
                    'title': dashboard_name + ' Repository Status'
                }
            }
        ]
    }

    cw.create_or_update_dashboard(dashboard_widget_mapping)
    out, err = capfd.readouterr()
    assert 'Dashboard input invalid. Could not create dashboard.' not in out

    updated_widgets = json.loads(cloudwatch.get_dashboard(DashboardName=dashboard_name)['DashboardBody'])['widgets']
    assert len(updated_widgets) == 1


def test_create_or_update_dashboard_invalid_widgets_to_put(monkeypatch, capfd, aws_credentials):
    cloudwatch = botocore.session.get_session().create_client('cloudwatch')
    stubber = Stubber(cloudwatch)
    stubber.add_response('list_dashboards', {'DashboardEntries': []})
    stubber.add_response('get_dashboard', {'DashboardBody': json.dumps({'widgets': []})})
    stubber.add_response('put_dashboard', {})
    stubber.activate()

    dashboard_name = 'dash-name'
    monkeypatch.setenv("dashboard_name", dashboard_name)

    dashboard_widget_mapping = {
        dashboard_name: [
            {
                'type': 'metric',
                'width': 6,
                'height': 6,
                'properties': {
                    'metrics': {},
                    'view': 'singleValue',
                    'period': 3600,
                    'stat': 'Maximum',
                    'region': os.environ['AWS_REGION'],
                    'title': dashboard_name + ' Repository Status'
                }
            }
        ]
    }

    cw.create_or_update_dashboard(dashboard_widget_mapping)
    out, err = capfd.readouterr()
    assert 'Dashboard input invalid. Could not create dashboard.' in out


@patch('lambda_dir.cloudwatch_interactions.cloudwatch.get_metric_data')
@patch('lambda_dir.cloudwatch_interactions.put_metrics_in_cloudwatch')
@patch('lambda_dir.cloudwatch_interactions.new_metric')
def test_create_activity_widget(mock_new_metric, mock_put_metrics, mock_get, capfd, monkeypatch):
    monkeypatch.setenv('namespace', 'test-namespace')
    monkeypatch.setenv('AWS_REGION', 'test-region')
    expected_metric_names = [
        'PRs Merged',
        'PRs Closed',
        'PRs Opened',
        'Issues Closed',
        'Issues Opened',
        'Releases Published',
        'Pushes to Master'
    ]
    mock_get.return_value = {
        'MetricDataResults': [{'Label': name, 'Values': []} for name in expected_metric_names],
    }
    mock_new_metric.side_effect = lambda repo, name, value: print(repo, name, value)
    mock_put_metrics.return_value = {}

    activity_widget = cw.create_activity_widget('test-repo-name')
    out, err = capfd.readouterr()
    for metric_name in expected_metric_names:
        assert 'test-repo-name ' + metric_name + ' 0' in out

    assert activity_widget == {
        'type': 'metric',
        'width': 6,
        'height': 9,
        'properties': {
            'metrics': [['test-namespace', name, 'REPO_NAME', 'test-repo-name'] for name in expected_metric_names],
            'view': 'singleValue',
            'period': 86400,
            'stat': 'Sum',
            'region': 'test-region',
            'title': 'test-repo-name Activity Over the Last 24 hours'
        }
    }