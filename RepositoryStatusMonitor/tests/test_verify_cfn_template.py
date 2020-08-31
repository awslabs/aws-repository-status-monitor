import json
import re
import subprocess

import pytest
from aws_cdk import core

from repository_status_monitor_stack import RepositoryStatusMonitorStack


def retrieve_template(github):
    try:
        with open('tests/template.json') as json_file:
            return json.dumps(json.load(json_file), indent=4, sort_keys=True)
    except FileNotFoundError:
        context = {
            'github_token': github,
            'repo_names': 'aws-node-termination-handler',
            'dashboard_name_prefix': 'test-dash', 
            'get_docker': 'y',
            'github_fields_unpaginated': 'Stars,stargazers_count;Forks,forks_count;Open Issues,open_issues_count;Watchers,subscribers_count',
            'github_fields_paginated': 'Open Pull Requests,pulls',
            'docker_fields': 'Pull Count,pull_count',
            'owner': 'aws',
            'namespace': 'open-source-dashboard',
            'user_agent_header': 'OpenSourceDashboard',
            'default_metric_widget_name': 'default_metric_widget_name',
            'default_text_widget_name': 'default_text_widget_name'
        }
        app = core.App(context=context)
        RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor')
        template = app.synth().get_stack('RepositoryStatusMonitor').template
        with open('tests/template.json', 'w') as json_file:
            json.dump(template, json_file, indent=4)
        return json.dumps(template, indent=4, sort_keys=True)

@pytest.fixture(scope='session', autouse=True)
def remove_template():
    yield
    remove_template_file = subprocess.run(['rm', 'tests/template.json'], capture_output=True)
    if remove_template_file.returncode != 0:
        print(remove_template_file.stderr.decode('utf-8'))

def test_two_queues_created(github):
    assert retrieve_template(github).count('AWS::SQS::Queue') == 2

def test_dead_letter_queue_created(github):
    assert '"QueueName": "DeadLetterQueue"' in retrieve_template(github)

def test_webhook_queue_created(github):
    assert '"QueueName": "WebhookQueue"' in retrieve_template(github) 

def test_both_custom_roles_created(github):
    assert retrieve_template(github).count('AWS::IAM::Role' ) >= 2 

def test_metric_handler_management_role_created(github):
    assert '"RoleName": "MetricHandlerManagementRole"' in retrieve_template(github) 

def test_webhook_creator_role_created(github):
    assert '"RoleName": "WebhookCreatorRole"' in retrieve_template(github) 

def test_both_custom_policies_created(github):
    assert retrieve_template(github).count('AWS::IAM::Policy' ) >= 2 

def test_metric_handler_management_role_default_policy_created(github):
    assert '"PolicyName": "MetricHandlerManagementRoleDefaultPolicy' in retrieve_template(github)

def test_metric_handler_management_role_default_policy_has_correct_actions(github):
    assert 'cloudwatch:GetDashboard' in retrieve_template(github)
    assert 'cloudwatch:ListDashboards' in retrieve_template(github)
    assert 'cloudwatch:PutDashboard' in retrieve_template(github)
    assert 'cloudwatch:PutMetricData' in retrieve_template(github)
    assert 'logs:CreateLogGroup' in retrieve_template(github)
    assert 'logs:CreateLogStream' in retrieve_template(github)
    assert 'logs:PutLogEvents' in retrieve_template(github)
    assert 'secretsmanager:GetSecretValue' in retrieve_template(github)

def test_webhook_creator_role_default_policy_created(github):
    assert '"PolicyName": "WebhookCreatorRoleDefaultPolicy' in retrieve_template(github)

def test_webhook_creator_role_default_policy_has_correct_actions(github):
    assert '"Action": "secretsmanager:GetSecretValue"' in retrieve_template(github)

def test_both_lambdas_created(github):
    assert retrieve_template(github).count('AWS::Lambda::Function' ) == 2

def test_metric_handler_lambda_created(github):
    assert '"FunctionName": "MetricsHandler"' in retrieve_template(github)

def test_webhook_creator_lambda_created(github):
    assert '"FunctionName": "WebhookCreator"' in retrieve_template(github)

def test_metric_handler_eventbridge_rule_created(github):
    assert 'AWS::Events::Rule' in retrieve_template(github)

def test_webhook_queue_event_source_mapping_created(github):
    assert 'AWS::Lambda::EventSourceMapping' in retrieve_template(github)

def test_api_gateway_created(github):
    assert 'AWS::ApiGateway::RestApi' in retrieve_template(github)

def test_api_gateway_has_post_method(github):
    assert 'AWS::ApiGateway::Method' in retrieve_template(github)

def test_lambda_name_correct(github):
    assert 'MetricsHandler' in retrieve_template(github)

def test_rule_created(github):
    assert 'AWS::Events::Rule' in retrieve_template(github)

def test_rule_correct(github):
    assert '"Name": "HourlyMetricRetrieval"' in retrieve_template(github)

def test_rule_name_correct(github):
    assert 'HourlyMetricRetrieval' in retrieve_template(github)

def test_rule_schedule_correct(github):
    assert 'rate(1 hour)' in retrieve_template(github)

def test_lambda_permission_for_rule_created(github):
    assert 'AWS::Lambda::Permission' in retrieve_template(github)


