import json
import os

import boto3

import http_handler as hh


def handler(event, context):
    """Creates webhooks on the specified repositories for the specified events to be posted to the API Gateway URL

    :param event: information about what is invoking the function
    :type event: usually dict, but can also be list, str, int, float, NoneType
    :param context: information provided by AWS Lambda about the invocation, function, and execution environment
    :type context: LambdaContext
    """
    events = ['issues', 'pull_request', 'release', 'push']
    for repo_name in os.environ['repo_names'].split(','):
        owner = os.environ['owner']
        if '/' in repo_name:
            [owner, repo_name] = repo_name.split('/')
        github_url = 'https://api.github.com/repos/' + owner + '/' + repo_name + '/hooks'
        github_headers = {
            'Authorization': 'token ' + boto3.client('secretsmanager').get_secret_value(SecretId='github_auth_token')[
                'SecretString'],
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json',
            'User-Agent': os.environ['user_agent_header']
        }

        payload = json.dumps({
            'active': True,
            'name': 'web',
            'events': events,
            'config': {
                'url': os.environ['apigw_endpoint'],
                'content_type': 'json',
                'insecure_ssl': '0'
            }
        })

        success, data, headers = hh.request_handler(github_url, method='POST', headers=github_headers,
                                                    post_body=payload)
        if success:
            print('%s webhook created' % ', '.join(events))
        else:
            fail_message = data['errors'][0]['message'] if 'errors' in data.keys() else data['message']
            print('Error creating webhook for repository %s for events %s: %s' %
                  (repo_name, ', '.join(events), fail_message))
