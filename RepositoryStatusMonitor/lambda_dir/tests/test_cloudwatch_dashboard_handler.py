import json
from unittest.mock import Mock, patch

import boto3
from moto import mock_sqs

from lambda_dir import cloudwatch_dashboard_handler as cdh


def set_environment(monkeypatch):
    monkeypatch.setenv('repo_names', 'test-repo-name')
    monkeypatch.setenv('owner', 'test-owner')
    monkeypatch.setenv('dashboard_name_prefix', 'test-dashboard-name-prefix')
    monkeypatch.setenv('default_metric_widget_name', 'test-metric-widget-name')
    monkeypatch.setenv('default_text_widget_name', 'test-text-widget-name')


def get_metric_and_widget_data():
    sorted_widgets = {
        'test-main': {
            'type': 'metric',
            'dashboard_level': 'main',
            'data': {'test': 1}
        },
        'test-details': {
            'type': 'text',
            'dashboard_level': 'details',
            'data': {'test1': 'test2'}
        }
    }

    metric_widget = {
        'type': 'metric',
        'width': 6,
        'height': 3,
        'properties': {
            'metrics': [['test-namespace', 'test', 'REPO_NAME', 'test-repo-name']],
            'view': 'singleValue',
            'period': 3600,
            'stat': 'Maximum',
            'region': 'us-west-2',
            'title': 'test-repo test-main'
        }
    }

    text_widget = {
        'type': 'text',
        'height': 3,
        'properties': {
            'markdown': '## test-repo-name test-details\n Name | Value \n ----|----- \ntest1 | test2\n'
        }
    }

    return_data = {
        'test-dashboard-name-prefix': [
            metric_widget,
            {'test-activity': 'activity'}
        ],
        'test-dashboard-name-prefix-test-repo-name': [
            text_widget
        ]
    }

    return sorted_widgets, metric_widget, text_widget, return_data


@mock_sqs
@patch('lambda_dir.cloudwatch_dashboard_handler.create_and_put_metrics_and_widgets')
@patch('lambda_dir.cloudwatch_dashboard_handler.cw_interactions.create_or_update_dashboard')
@patch('lambda_dir.cloudwatch_dashboard_handler.handle_webhook_events.handle_webhook')
def test_handler_records_in_events_valid_widgets(mock_handle_webhook, mock_crud, mock_mw, aws_credentials, monkeypatch):
    mock_handle_webhook.return_value = {'metric': 'metric'}

    with mock_sqs():
        boto3.setup_default_session()
        sqs = boto3.client('sqs')
        test_queue = sqs.create_queue(
            QueueName='TestQueue'
        )
        response = sqs.send_message(
            QueueUrl=test_queue['QueueUrl'],
            MessageBody='hello'
        )
        messages = sqs.receive_message(
            QueueUrl=test_queue['QueueUrl']
        )
        monkeypatch.setenv('queue_url', test_queue['QueueUrl'])
        event = {'Records': [{'body': json.dumps('123'), 'receiptHandle': messages['Messages'][0]['ReceiptHandle']}]}
        cdh.handler(event, None)
        mock_handle_webhook.assert_called_once()
        mock_crud.assert_called_once()
        mock_mw.assert_not_called()


@mock_sqs
@patch('lambda_dir.cloudwatch_dashboard_handler.create_and_put_metrics_and_widgets')
@patch('lambda_dir.cloudwatch_dashboard_handler.cw_interactions.create_or_update_dashboard')
@patch('lambda_dir.cloudwatch_dashboard_handler.handle_webhook_events.handle_webhook')
def test_handler_records_in_events_no_valid_widgets(mock_handle_webhook, mock_crud, mock_mw, capfd, aws_credentials,
                                                    monkeypatch):
    mock_handle_webhook.return_value = {}

    with mock_sqs():
        boto3.setup_default_session()
        sqs = boto3.client('sqs')
        test_queue = sqs.create_queue(
            QueueName='TestQueue'
        )
        response = sqs.send_message(
            QueueUrl=test_queue['QueueUrl'],
            MessageBody='hello'
        )
        messages = sqs.receive_message(
            QueueUrl=test_queue['QueueUrl']
        )
        monkeypatch.setenv('queue_url', test_queue['QueueUrl'])
        event = {'Records': [{'body': json.dumps('123'), 'receiptHandle': messages['Messages'][0]['ReceiptHandle']}]}
        cdh.handler(event, None)
        mock_handle_webhook.assert_called_once()
        mock_crud.assert_not_called()
        mock_mw.assert_not_called()
        assert 'No valid widgets, dashboard cannot be created.' in capfd.readouterr()[0]


@mock_sqs
@patch('lambda_dir.cloudwatch_dashboard_handler.create_and_put_metrics_and_widgets')
@patch('lambda_dir.cloudwatch_dashboard_handler.cw_interactions.create_or_update_dashboard')
@patch('lambda_dir.cloudwatch_dashboard_handler.handle_webhook_events.handle_webhook')
def test_handler_records_not_in_events_no_valid_widgets(mock_handle_webhook, mock_crud, mock_mw, capfd, aws_credentials,
                                                        monkeypatch):
    mock_mw.return_value = {}

    with mock_sqs():
        boto3.setup_default_session()
        sqs = boto3.client('sqs')
        test_queue = sqs.create_queue(
            QueueName='TestQueue'
        )
        response = sqs.send_message(
            QueueUrl=test_queue['QueueUrl'],
            MessageBody='hello'
        )
        messages = sqs.receive_message(
            QueueUrl=test_queue['QueueUrl']
        )
        monkeypatch.setenv('queue_url', test_queue['QueueUrl'])
        cdh.handler({}, None)
        mock_handle_webhook.assert_not_called()
        mock_crud.assert_not_called()
        mock_mw.assert_called_once()
        assert 'No valid widgets, dashboard cannot be created.' in capfd.readouterr()[0]


@mock_sqs
@patch('lambda_dir.cloudwatch_dashboard_handler.create_and_put_metrics_and_widgets')
@patch('lambda_dir.cloudwatch_dashboard_handler.cw_interactions.create_or_update_dashboard')
@patch('lambda_dir.cloudwatch_dashboard_handler.handle_webhook_events.handle_webhook')
def test_handler_records_not_in_events_valid_widgets(mock_handle_webhook, mock_crud, mock_mw, aws_credentials,
                                                     monkeypatch):
    mock_mw.return_value = {'metric': 'metric'}

    with mock_sqs():
        boto3.setup_default_session()
        sqs = boto3.client('sqs')
        test_queue = sqs.create_queue(
            QueueName='TestQueue'
        )
        response = sqs.send_message(
            QueueUrl=test_queue['QueueUrl'],
            MessageBody='hello'
        )
        messages = sqs.receive_message(
            QueueUrl=test_queue['QueueUrl']
        )
        monkeypatch.setenv('queue_url', test_queue['QueueUrl'])
        cdh.handler({}, None)
        mock_handle_webhook.assert_not_called()
        mock_crud.assert_called_once()
        mock_mw.assert_called_once()


@mock_sqs
@patch('lambda_dir.cloudwatch_dashboard_handler.cw_interactions.create_activity_widget')
@patch('lambda_dir.cloudwatch_dashboard_handler.github_docker.aggregate_metrics')
@patch('lambda_dir.cloudwatch_dashboard_handler.cw_interactions.create_text_widget')
@patch('lambda_dir.cloudwatch_dashboard_handler.cw_interactions.create_metric_widget')
def test_create_and_put_metrics_and_widgets(mock_cmw, mock_ctw, mock_aggregate, mock_caw, aws_credentials, monkeypatch):
    set_environment(monkeypatch)
    sorted_widgets, metric_widget, text_widget, return_data = get_metric_and_widget_data()
    mock_aggregate.return_value = sorted_widgets
    mock_cmw.return_value = metric_widget
    mock_ctw.return_value = text_widget
    mock_caw.return_value = {'test-activity': 'activity'}
    widgets = cdh.create_and_put_metrics_and_widgets()
    mock_aggregate.assert_called_once_with('test-owner', 'test-repo-name')
    assert widgets == return_data


@mock_sqs
@patch('lambda_dir.cloudwatch_dashboard_handler.cw_interactions.create_activity_widget')
@patch('lambda_dir.cloudwatch_dashboard_handler.github_docker.aggregate_metrics')
@patch('lambda_dir.cloudwatch_dashboard_handler.cw_interactions.create_text_widget')
@patch('lambda_dir.cloudwatch_dashboard_handler.cw_interactions.create_metric_widget')
def test_create_and_put_metrics_and_widgets_slash_in_repo_name(mock_cmw, mock_ctw, mock_aggregate, mock_caw,
                                                               aws_credentials, monkeypatch):
    set_environment(monkeypatch)
    monkeypatch.setenv('owner', 'bad-owner')
    monkeypatch.setenv('repo_names', 'test-owner/test-repo-name')
    sorted_widgets, metric_widget, text_widget, return_data = get_metric_and_widget_data()
    mock_aggregate.return_value = sorted_widgets
    mock_cmw.return_value = metric_widget
    mock_ctw.return_value = text_widget
    mock_caw.return_value = {'test-activity': 'activity'}
    widgets = cdh.create_and_put_metrics_and_widgets()
    mock_aggregate.assert_called_once_with('test-owner', 'test-repo-name')
    assert widgets == return_data


@mock_sqs
@patch('lambda_dir.cloudwatch_dashboard_handler.cw_interactions.create_activity_widget')
@patch('lambda_dir.cloudwatch_dashboard_handler.github_docker.aggregate_metrics')
@patch('lambda_dir.cloudwatch_dashboard_handler.cw_interactions.create_text_widget')
@patch('lambda_dir.cloudwatch_dashboard_handler.cw_interactions.create_metric_widget')
def test_create_and_put_metrics_and_widgets_invalid_widget_type(mock_cmw, mock_ctw, mock_aggregate, mock_caw, capfd,
                                                                aws_credentials, monkeypatch):
    set_environment(monkeypatch)
    sorted_widgets, metric_widget, text_widget, return_data = get_metric_and_widget_data()
    sorted_widgets['test-main']['type'] = 'test-bad-type'
    return_data['test-dashboard-name-prefix'] = [
        {'test-activity': 'activity'}
    ]

    mock_aggregate.return_value = sorted_widgets
    mock_cmw.return_value = metric_widget
    mock_ctw.return_value = text_widget
    mock_caw.return_value = {'test-activity': 'activity'}
    widgets = cdh.create_and_put_metrics_and_widgets()
    out, err = capfd.readouterr()
    assert 'Invalid widget type specified for widget: test-main' in out
    assert widgets == return_data
