from unittest.mock import Mock, patch

import boto3
import pytest
from moto import mock_secretsmanager

from lambda_dir import webhook_creator as wc


def set_environment(monkeypatch):
    monkeypatch.setenv("repo_names", "test-repo")
    monkeypatch.setenv("owner", "test-owner")
    monkeypatch.setenv("user_agent_header", "test-user-agent-header")
    monkeypatch.setenv("apigw_endpoint", "test-apigw-endpoint")


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


@patch('lambda_dir.webhook_creator.hh.request_handler')
def test_handler_good_github_response(mock_post, aws_credentials, capfd, monkeypatch):
    set_environment(monkeypatch)
    mock_post.return_value = True, {'message': 'Test Good'}, {}

    wc.handler({}, None)
    assert 'issues, pull_request, release, push webhook created' in capfd.readouterr()[0]


@patch('lambda_dir.webhook_creator.hh.request_handler')
def test_handler_bad_github_response(mock_post, aws_credentials, capfd, monkeypatch):
    set_environment(monkeypatch)
    mock_post.return_value = False, {'message': 'bad response'}, {}

    wc.handler({}, None)
    assert 'Error creating webhook for repository test-repo for events issues, pull_request, release, push: bad response' in capfd.readouterr()[0]


@patch('lambda_dir.webhook_creator.hh.request_handler')
def test_handler_bad_github_response_errors_in_keys(mock_post, aws_credentials, capfd, monkeypatch):
    set_environment(monkeypatch)
    data = {'errors': [{'message': 'errors in keys'}]} 
    mock_post.return_value = False, data, {}

    wc.handler({}, None)
    assert 'Error creating webhook for repository test-repo for events issues, pull_request, release, push: errors in keys' in capfd.readouterr()[0]

