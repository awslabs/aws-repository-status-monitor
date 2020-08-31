import json

import pytest
from aws_cdk import core
from unittest.mock import Mock, patch

from repository_status_monitor_stack import RepositoryStatusMonitorStack

def set_context(github: str) -> dict:
    return {
        'repo_names': 'aws-node-termination-handler',
        'dashboard_name_prefix': 'test-dash', 
        'get_docker': 'y',
        'github_token': github,
        'github_fields_unpaginated': 'Stars,stargazers_count;Forks,forks_count;Open Issues,open_issues_count;Watchers,subscribers_count',
        'github_fields_paginated': 'Open Pull Requests,pulls',
        'docker_fields': 'Pull Count,pull_count',
        'owner': 'aws',
        'namespace': 'open-source-dashboard',
        'user_agent_header': 'OpenSourceDashboard',
        'default_metric_widget_name': 'default_metric_widget_name',
        'default_text_widget_name': 'default_text_widget_name'
    }

@patch('lambda_dir.http_handler.request_handler')
def test_with_good_context(mock_get, capfd, github):
    data = [
        {   
            'name': 'aws-node-termination-handler', 
            'owner': {
                'login': 'aws' 
            }
        }
    ]
    mock_get.return_value = True, data, {}
    context = set_context(github)
    app = core.App(context=context)
    stack = RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')
    out, err = capfd.readouterr()
    assert 'Valid repositories: aws-node-termination-handler' in out
    assert 'Invalid repositories: none' in out
    

def test_missing_github_token():
    with pytest.raises(ValueError, match='Need to specify GitHub token.'):
        context = set_context("")
        context.pop('github_token')
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')

def test_empty_github_token():
    with pytest.raises(ValueError, match='Need to specify GitHub token.'):
        context = set_context("")
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')


def test_missing_dashboard_name_prefix(github):
    with pytest.raises(ValueError, match='Need to specify prefix for dashboard names.'):
        context = set_context(github)
        context.pop('dashboard_name_prefix')
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')


def test_empty_dashboard_name_prefix(github):
    with pytest.raises(ValueError, match='Need to specify prefix for dashboard names.'):
        context = set_context(github)
        context['dashboard_name_prefix'] = ""
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')


def test_missing_repo_names(github):
    with pytest.raises(ValueError, match='Need to specify repository names.'):
        context = set_context(github)
        context.pop('repo_names')
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')


def test_empty_repo_names(github):
    with pytest.raises(ValueError, match='Need to specify repository names.'):
        context = set_context(github)
        context['repo_names'] = ""
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')


def test_missing_docker_preference(github):
    with pytest.raises(ValueError, match='Need to specify whether to include docker metrics.'):
        context = set_context(github)
        context.pop('get_docker')
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')


def test_empty_docker_preference(github):
    with pytest.raises(ValueError, match='Need to specify whether to include docker metrics.'):
        context = set_context(github)
        context['get_docker'] = ""
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')


def test_missing_owner(github):
    with pytest.raises(ValueError, match='Need to specify GitHub owner.'):
        context = set_context(github)
        context.pop('owner')
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')


def test_namespace_missing(github):
    with pytest.raises(ValueError, match='Need to specify namespace for CloudWatch metrics.'):
        context = set_context(github)
        context.pop('namespace')
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')


def test_namespace_empty(github):
    with pytest.raises(ValueError, match='Need to specify namespace for CloudWatch metrics.'):
        context = set_context(github)
        context['namespace'] = ""
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')


def test_user_agent_header_missing(github):
    with pytest.raises(ValueError, match='Need to specify User-Agent header for GitHub requests.'):
        context = set_context(github)
        context.pop('user_agent_header')
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')


def test_user_agent_header_empty(github):
    with pytest.raises(ValueError, match='Need to specify User-Agent header for GitHub requests.'):
        context = set_context(github)
        context['user_agent_header'] = ""
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')


@patch('lambda_dir.http_handler.request_handler')
def test_bad_github_credentials(mock_get):
    with pytest.raises(RuntimeError, match='Bad credentials'):
        context = set_context("1234")
        data = {'message': 'Bad credentials'}
        mock_get.return_value = False, data, {}
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')


@patch('lambda_dir.http_handler.request_handler')
def test_invalid_repo_names(mock_get, github):
    with pytest.raises(RuntimeError, match='All repository names must be valid.'):
        data = [
            {   
                'name': 'aws-node-termination-handler', 
                'owner': {
                    'login': 'aws' 
                }
            }
        ]
        mock_get.return_value = True, data, {}
        
        context = set_context(github)
        context['repo_names'] = 'aws-node-termination-handler,hello'
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')


@patch('lambda_dir.http_handler.request_handler')
def test_no_valid_repo_names(mock_get, github):
     with pytest.raises(RuntimeError, match='All repository names must be valid.'):
        data = [
            {   
                'name': 'aws-node-termination-handler', 
                'owner': {
                    'login': 'aws' 
                }
            }
        ]
        mock_get.return_value = True, data, {}
        context = set_context(github)
        context['repo_names'] = 'hello,goodbye'
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')

    
@patch('lambda_dir.http_handler.request_handler')
def test_invalid_repo_names_format(mock_get, github):
    with pytest.raises(RuntimeError, match='All repository names must be valid.'):
        data = [
            {   
                'name': 'aws-node-termination-handler', 
                'owner': {
                    'login': 'aws' 
                }
            },
            {   
                'name': 'amazon-ec2-metadata-mock', 
                'owner': {
                    'login': 'aws' 
                }
            }
        ]
        mock_get.return_value = True, data, {}
        context = set_context(github)
        context['repo_names'] = 'aws-node-termination-handler;amazon-ec2-metadata-mock'
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')
    

@patch('lambda_dir.http_handler.request_handler')
def test_no_owner_specified(mock_get, github):
    with pytest.raises(RuntimeError, match='All repository names must be valid.'):
        data = [
            {   
                'name': 'aws-node-termination-handler', 
                'owner': {
                    'login': 'aws' 
                }
            },
            {   
                'name': 'amazon-ec2-metadata-mock', 
                'owner': {
                    'login': 'aws' 
                }
            }
        ]
        mock_get.return_value = True, data, {}
        context = set_context(github)
        context['owner'] = ''
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')

@patch('lambda_dir.http_handler.request_handler')
def test_individual_owner_not_specified_and_general_owner_wrong(mock_get, github):
    with pytest.raises(RuntimeError, match='All repository names must be valid.'):
        data = [
            {   
                'name': 'aws-node-termination-handler', 
                'owner': {
                    'login': 'aws' 
                }
            }
        ]
        mock_get.return_value = True, data, {}
        context = set_context(github)
        context['owner'] = 'amazon'
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')


@patch('lambda_dir.http_handler.request_handler')
def test_individual_owner_takes_precedence_over_general_owner(mock_get, capfd, github):
    data = [
        {   
            'name': 'aws-node-termination-handler', 
            'owner': {
                'login': 'aws' 
            }
        },
        {   
            'name': 'amazon-ec2-metadata-mock', 
            'owner': {
                'login': 'amazon' 
            }
        }
    ]
    mock_get.return_value = True, data, {}
    context = set_context(github)
    context['owner'] = 'amazon'
    context['repo_names'] = 'aws/aws-node-termination-handler,amazon-ec2-metadata-mock'
    app = core.App(context=context)
    RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')
    out, err = capfd.readouterr()
    assert 'Valid repositories: aws/aws-node-termination-handler, amazon-ec2-metadata-mock' in out
    assert 'Invalid repositories: none' in out

@patch('lambda_dir.http_handler.request_handler')
def test_all_individual_owners_specified(mock_get, capfd, github):
    data = [
        {   
            'name': 'aws-node-termination-handler', 
            'owner': {
                'login': 'aws' 
            }
        },
        {   
            'name': 'amazon-ec2-metadata-mock', 
            'owner': {
                'login': 'aws' 
            }
        }
    ]
    mock_get.return_value = True, data, {}
    context = set_context(github)
    context['owner'] = ''
    context['repo_names'] = 'aws/aws-node-termination-handler,aws/amazon-ec2-metadata-mock'
    app = core.App(context=context)
    RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')
    out, err = capfd.readouterr()
    assert 'Valid repositories: aws/aws-node-termination-handler, aws/amazon-ec2-metadata-mock' in out
    assert 'Invalid repositories: none' in out


@patch('lambda_dir.http_handler.request_handler')
def test_all_individual_owners_specified_but_some_wrong(mock_get, github):
    with pytest.raises(RuntimeError, match='All repository names must be valid.'):
        data = [
            {   
                'name': 'aws-node-termination-handler', 
                'owner': {
                    'login': 'aws' 
                }
            },
            {   
                'name': 'amazon-ec2-metadata-mock', 
                'owner': {
                    'login': 'aws' 
                }
            }
        ]
        mock_get.return_value = True, data, {}
        context = set_context(github)
        context['owner'] = ''
        context['repo_names'] = 'aws/aws-node-termination-handler,amazon/amazon-ec2-metadata-mock'
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')