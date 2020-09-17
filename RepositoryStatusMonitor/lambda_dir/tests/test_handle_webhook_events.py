from unittest.mock import call, patch

import boto3
import pytest
from moto import mock_secretsmanager

from lambda_dir import handle_webhook_events as hw


@mock_secretsmanager
@pytest.fixture(scope='module', autouse=True)
def create_secret():
    with mock_secretsmanager():
        boto3.setup_default_session()
        boto3.client('secretsmanager').create_secret(
            Name='github_auth_token',
            SecretString='1234'
        )
        yield


def set_environment(monkeypatch):
    monkeypatch.setenv('dashboard_name_prefix', 'test-dashboard-name-prefix')
    monkeypatch.setenv('user_agent_header', 'test-user-agent-header')
    monkeypatch.setenv('owner', 'test-owner')


def get_payload(payload_type: str):
    payloads = {
        'issue': {
            "action": "closed",
            "issue": {
                "created_at": "2019-05-15T15:20:18Z",
                "closed_at": "2019-05-15T15:40:18Z",
            },
            "repository": {
                "name": "test-repo-name"
            }
        },
        'pr': {
            "action": "closed",
            "pull_request": {
                "created_at": "2019-05-15T15:20:18Z",
                "closed_at": "2019-05-15T15:40:18Z",
            },
            "repository": {
                "name": "test-repo-name"
            }
        },
        'release': {
            "action": "published",
            "release": {
                "published_at": "2019-05-15T15:40:18Z"
            },
            "repository": {
                "name": "test-repo-name",
                "owner": {
                    "login": "aws"
                }
            }
        },
        'push': {
            'ref': 'refs/heads/master',
            "pusher": {
                "name": "pusher"
            },
            "repository": {
                "name": "test-repo-name"
            }
        },
        'bad_event': {
            "action": "closed",
            "bad": {
                "created_at": "2019-05-15T15:20:18Z",
                "closed_at": "2019-05-15T15:40:18Z",
            },
            "repository": {
                "name": "test-repo-name"
            }
        },

    }
    return payloads[payload_type]


@patch('lambda_dir.handle_webhook_events.handle_issues')
@patch('lambda_dir.handle_webhook_events.handle_prs')
@patch('lambda_dir.handle_webhook_events.handle_releases')
@patch('lambda_dir.handle_webhook_events.handle_pushes')
def test_handle_webhook_issue(mock_push, mock_release, mock_pr, mock_issue, monkeypatch):
    set_environment(monkeypatch)
    mock_issue.return_value = {'test-issue': 'test'}
    payload = get_payload('issue')

    handle_webhook_return = hw.handle_webhook(payload)
    mock_push.assert_not_called()
    mock_release.assert_not_called()
    mock_pr.assert_not_called()
    mock_issue.assert_called_once_with(payload, 'test-dashboard-name-prefix')
    assert handle_webhook_return == {'test-issue': 'test'}


@patch('lambda_dir.handle_webhook_events.handle_issues')
@patch('lambda_dir.handle_webhook_events.handle_prs')
@patch('lambda_dir.handle_webhook_events.handle_releases')
@patch('lambda_dir.handle_webhook_events.handle_pushes')
def test_handle_webhook_pr(mock_push, mock_release, mock_pr, mock_issue, monkeypatch):
    set_environment(monkeypatch)
    mock_pr.return_value = {'test-pr': 'test'}
    payload = get_payload('pr')

    handle_webhook_return = hw.handle_webhook(payload)
    mock_push.assert_not_called()
    mock_release.assert_not_called()
    mock_issue.assert_not_called()
    mock_pr.assert_called_once_with(payload, 'test-dashboard-name-prefix')
    assert handle_webhook_return == {'test-pr': 'test'}


@patch('lambda_dir.handle_webhook_events.handle_issues')
@patch('lambda_dir.handle_webhook_events.handle_prs')
@patch('lambda_dir.handle_webhook_events.handle_releases')
@patch('lambda_dir.handle_webhook_events.handle_pushes')
def test_handle_webhook_release(mock_push, mock_release, mock_pr, mock_issue, monkeypatch):
    set_environment(monkeypatch)
    mock_release.return_value = {'test-release': 'test'}
    payload = get_payload('release')

    handle_webhook_return = hw.handle_webhook(payload)
    mock_push.assert_not_called()
    mock_pr.assert_not_called()
    mock_issue.assert_not_called()
    mock_release.assert_called_once_with(payload, 'test-dashboard-name-prefix')
    assert handle_webhook_return == {'test-release': 'test'}


@patch('lambda_dir.handle_webhook_events.handle_issues')
@patch('lambda_dir.handle_webhook_events.handle_prs')
@patch('lambda_dir.handle_webhook_events.handle_releases')
@patch('lambda_dir.handle_webhook_events.handle_pushes')
def test_handle_webhook_push(mock_push, mock_release, mock_pr, mock_issue, monkeypatch):
    set_environment(monkeypatch)
    mock_push.return_value = {'test-push': 'test'}
    payload = get_payload('push')

    handle_webhook_return = hw.handle_webhook(payload)
    mock_release.assert_not_called()
    mock_pr.assert_not_called()
    mock_issue.assert_not_called()
    mock_push.assert_called_once_with(payload)
    assert handle_webhook_return == {'test-push': 'test'}


@patch('lambda_dir.handle_webhook_events.handle_issues')
@patch('lambda_dir.handle_webhook_events.handle_prs')
@patch('lambda_dir.handle_webhook_events.handle_releases')
@patch('lambda_dir.handle_webhook_events.handle_pushes')
def test_handle_webhook_other_event(mock_push, mock_release, mock_pr, mock_issue, monkeypatch):
    set_environment(monkeypatch)
    payload = get_payload('bad_event')
    handle_webhook_return = hw.handle_webhook(payload)
    mock_release.assert_not_called()
    mock_pr.assert_not_called()
    mock_issue.assert_not_called()
    mock_push.assert_not_called()
    assert not handle_webhook_return


@patch('lambda_dir.handle_webhook_events.create_issue_or_pr_widget')
@patch('lambda_dir.handle_webhook_events.cw_interactions.put_metrics_in_cloudwatch')
@patch('lambda_dir.handle_webhook_events.cw_interactions.new_metric')
def test_handle_prs_closed_and_merged(mock_new_metric, mock_put_metrics, mock_create_widget):
    mock_new_metric.side_effect = ['merged', 'closed']
    mock_create_widget.return_value = {'test-widget': 'pull_request'}
    payload = get_payload('pr')
    payload['pull_request']['merged'] = True
    handle_prs_return = hw.handle_prs(payload, 'test-dashboard-name-prefix')
    mock_put_metrics.assert_has_calls([call(['merged']), call(['closed'])])
    assert handle_prs_return == {'test-widget': 'pull_request'}


@patch('lambda_dir.handle_webhook_events.create_issue_or_pr_widget')
@patch('lambda_dir.handle_webhook_events.cw_interactions.put_metrics_in_cloudwatch')
@patch('lambda_dir.handle_webhook_events.cw_interactions.new_metric')
def test_handle_prs_closed_not_merged(mock_new_metric, mock_put_metrics, mock_create_widget):
    mock_new_metric.return_value = 'closed'
    mock_create_widget.return_value = {'test-widget': 'pull_request'}
    payload = get_payload('pr')
    payload['pull_request']['merged'] = False
    handle_prs_return = hw.handle_prs(payload, 'test-dashboard-name-prefix')
    mock_put_metrics.assert_called_once_with(['closed'])
    assert handle_prs_return == {'test-widget': 'pull_request'}


@patch('lambda_dir.handle_webhook_events.create_issue_or_pr_widget')
@patch('lambda_dir.handle_webhook_events.cw_interactions.put_metrics_in_cloudwatch')
@patch('lambda_dir.handle_webhook_events.cw_interactions.new_metric')
def test_handle_prs_opened(mock_new_metric, mock_put_metrics, mock_create_widget):
    mock_new_metric.return_value = 'opened'
    payload = get_payload('pr')
    payload['action'] = 'opened'
    handle_prs_return = hw.handle_prs(payload, 'test-dashboard-name-prefix')
    mock_put_metrics.assert_called_once_with(['opened'])
    mock_create_widget.assert_not_called()
    assert not handle_prs_return


@patch('lambda_dir.handle_webhook_events.create_issue_or_pr_widget')
@patch('lambda_dir.handle_webhook_events.cw_interactions.put_metrics_in_cloudwatch')
@patch('lambda_dir.handle_webhook_events.cw_interactions.new_metric')
def test_handle_prs_neither_opened_nor_closed(mock_new_metric, mock_put_metrics, mock_create_widget):
    payload = get_payload('pr')
    payload['action'] = 'assigned'
    handle_prs_return = hw.handle_prs(payload, 'test-dashboard-name-prefix')
    mock_new_metric.assert_not_called()
    mock_put_metrics.assert_not_called()
    mock_create_widget.assert_not_called()
    assert not handle_prs_return


@patch('lambda_dir.handle_webhook_events.create_issue_or_pr_widget')
@patch('lambda_dir.handle_webhook_events.cw_interactions.put_metrics_in_cloudwatch')
@patch('lambda_dir.handle_webhook_events.cw_interactions.new_metric')
def test_handle_issues_closed(mock_new_metric, mock_put_metrics, mock_create_widget):
    mock_new_metric.return_value = 'closed'
    mock_create_widget.return_value = {'test-widget': 'issue'}
    payload = get_payload('issue')
    handle_issues_return = hw.handle_issues(payload, 'test-dashboard-name-prefix')
    mock_put_metrics.assert_called_once_with(['closed'])
    assert handle_issues_return == {'test-widget': 'issue'}


@patch('lambda_dir.handle_webhook_events.create_issue_or_pr_widget')
@patch('lambda_dir.handle_webhook_events.cw_interactions.put_metrics_in_cloudwatch')
@patch('lambda_dir.handle_webhook_events.cw_interactions.new_metric')
def test_handle_issue_opened(mock_new_metric, mock_put_metrics, mock_create_widget):
    mock_new_metric.return_value = 'opened'
    payload = get_payload('issue')
    payload['action'] = 'opened'
    handle_issues_return = hw.handle_issues(payload, 'test-dashboard-name-prefix')
    mock_put_metrics.assert_called_once_with(['opened'])
    mock_create_widget.assert_not_called()
    assert not handle_issues_return


@patch('lambda_dir.handle_webhook_events.create_issue_or_pr_widget')
@patch('lambda_dir.handle_webhook_events.cw_interactions.put_metrics_in_cloudwatch')
@patch('lambda_dir.handle_webhook_events.cw_interactions.new_metric')
def test_handle_issues_neither_opened_nor_closed(mock_new_metric, mock_put_metrics, mock_create_widget):
    payload = get_payload('issue')
    payload['action'] = 'assigned'
    handle_issues_return = hw.handle_prs(payload, 'test-dashboard-name-prefix')
    mock_new_metric.assert_not_called()
    mock_put_metrics.assert_not_called()
    mock_create_widget.assert_not_called()
    assert not handle_issues_return


def mock_create_metric_widget_side_effect(repo_name: str, data: dict, title: str, view: str, id_str: str,
                                          granularity: str):
    print(data)
    print(title)
    return 'widget'


@patch('lambda_dir.handle_webhook_events.cw_interactions.create_metric_widget',
       side_effect=mock_create_metric_widget_side_effect)
def test_create_issue_or_pr_widget(mock_create_metric_widget, capfd):
    payload = get_payload('issue')
    payload['action'] = 'assigned'
    labels = {
        'key': 'issue',
        'name': 'Issue Duration',
        'title': ' Issues',
        'id': 'issues'
    }
    widget = hw.create_issue_or_pr_widget(payload, labels, 'test-dashboard-name-prefix')
    out, err = capfd.readouterr()
    assert "{'Issue Duration': 1200}" in out
    assert 'test-repo-name Issues' in out
    assert widget == {'test-dashboard-name-prefix-test-repo-name': ['widget']}


@patch('lambda_dir.handle_webhook_events.cw_interactions.create_metric_widget',
       side_effect=mock_create_metric_widget_side_effect)
@patch('lambda_dir.handle_webhook_events.hh.request_handler')
@patch('lambda_dir.handle_webhook_events.cw_interactions.new_metric')
@patch('lambda_dir.handle_webhook_events.cw_interactions.put_metrics_in_cloudwatch')
def test_handle_releases(mock_put_metrics, mock_new_metric, mock_get, mock_create_metric_widget, capfd, monkeypatch,
                         aws_credentials):
    mock_releases = [{'published_at': "2019-05-15T15:40:18Z"}, {'published_at': "2019-05-15T15:20:18Z"}]
    mock_get.return_value = True, mock_releases, {}
    set_environment(monkeypatch)
    payload = get_payload('release')

    handle_releases_return = hw.handle_releases(payload, 'test-dashboard-name-prefix')
    out, err = capfd.readouterr()
    mock_put_metrics.assert_called_once()
    mock_new_metric.assert_called_once()
    mock_get.assert_called_once()
    assert "{'Time Between Releases': 1200}" in out
    assert 'test-repo-name Releases' in out
    assert handle_releases_return == {'test-dashboard-name-prefix-test-repo-name': ['widget']}


@patch('lambda_dir.handle_webhook_events.cw_interactions.create_metric_widget',
       side_effect=mock_create_metric_widget_side_effect)
@patch('lambda_dir.handle_webhook_events.hh.request_handler')
@patch('lambda_dir.handle_webhook_events.cw_interactions.new_metric')
@patch('lambda_dir.handle_webhook_events.cw_interactions.put_metrics_in_cloudwatch')
def test_handle_releases_not_published(mock_put_metrics, mock_new_metric, mock_get, mock_create_metric_widget, capfd,
                                       monkeypatch):
    payload = get_payload('release')
    payload['action'] = 'other'
    handle_releases_return = hw.handle_releases(payload, 'test-dashboard-name-prefix')
    mock_put_metrics.assert_not_called()
    mock_new_metric.assert_not_called()
    mock_get.assert_not_called()
    mock_create_metric_widget.assert_not_called()
    assert not handle_releases_return


@patch('lambda_dir.handle_webhook_events.cw_interactions.create_metric_widget',
       side_effect=mock_create_metric_widget_side_effect)
@patch('lambda_dir.handle_webhook_events.hh.request_handler')
@patch('lambda_dir.handle_webhook_events.cw_interactions.new_metric')
@patch('lambda_dir.handle_webhook_events.cw_interactions.put_metrics_in_cloudwatch')
def test_handle_releases_bad_get(mock_put_metrics, mock_new_metric, mock_get, mock_create_metric_widget, capfd,
                                 monkeypatch):
    mock_get.return_value = False, [], {}
    set_environment(monkeypatch)
    payload = get_payload('release')

    handle_releases_return = hw.handle_releases(payload, 'test-dashboard-name-prefix')
    out, err = capfd.readouterr()
    mock_put_metrics.assert_called_once()
    mock_new_metric.assert_called_once()
    mock_get.assert_called_once()
    mock_create_metric_widget.assert_not_called()
    assert not handle_releases_return


@patch('lambda_dir.handle_webhook_events.cw_interactions.create_metric_widget',
       side_effect=mock_create_metric_widget_side_effect)
@patch('lambda_dir.handle_webhook_events.hh.request_handler')
@patch('lambda_dir.handle_webhook_events.cw_interactions.new_metric')
@patch('lambda_dir.handle_webhook_events.cw_interactions.put_metrics_in_cloudwatch')
def test_handle_releases_no_previous_release(mock_put_metrics, mock_new_metric, mock_get, mock_create_metric_widget,
                                             capfd, monkeypatch):
    mock_releases = [{'published_at': "2019-05-15T14:20:18Z"}]
    mock_get.return_value = True, mock_releases, {}
    set_environment(monkeypatch)
    payload = get_payload('release')

    handle_releases_return = hw.handle_releases(payload, 'test-dashboard-name-prefix')
    out, err = capfd.readouterr()
    mock_put_metrics.assert_called_once()
    mock_new_metric.assert_called_once()
    mock_get.assert_called_once()
    mock_create_metric_widget.assert_not_called()
    assert not handle_releases_return


@patch('lambda_dir.handle_webhook_events.cw_interactions.put_metrics_in_cloudwatch')
@patch('lambda_dir.handle_webhook_events.cw_interactions.new_metric')
def test_handle_push(mock_new_metric, mock_put_metrics):
    mock_new_metric.return_value = 'push'
    payload = get_payload('push')
    handle_pushes_return = hw.handle_pushes(payload)
    mock_put_metrics.assert_called_once_with(['push'])
    assert not handle_pushes_return


@patch('lambda_dir.handle_webhook_events.cw_interactions.put_metrics_in_cloudwatch')
@patch('lambda_dir.handle_webhook_events.cw_interactions.new_metric')
def test_handle_push_not_master(mock_new_metric, mock_put_metrics):
    payload = get_payload('release')
    payload['ref'] = 'refs/heads/test'
    handle_pushes_return = hw.handle_pushes(payload)
    mock_new_metric.assert_not_called()
    mock_put_metrics.assert_not_called()
    assert not handle_pushes_return
