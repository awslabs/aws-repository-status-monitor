import json
import os

import boto3

import cloudwatch_interactions as cw_interactions
import collect_github_docker_metrics as github_docker
import handle_webhook_events as handle_webhook_events


def handler(event, context) -> None:
    """Called when the Lambda function is invoked, creates or updates a CloudWatch dashboard

    :param event: information about what is invoking the function
    :type event: usually dict, but can also be list, str, int, float, NoneType
    :param context: information provided by AWS Lambda about the invocation, function, and execution environment
    :type context: LambdaContext
    """
    widgets = {}
    # If 'Records' is in event, the trigger is a GitHub webhook posting to the SQS Queue, not the EventBridge rule
    if 'Records' in event.keys():
        print("Updating widgets for a Webhook event")
        webhook_payload = json.loads(event['Records'][0]['body'])
        webhook_metric = handle_webhook_events.handle_webhook(webhook_payload)
        if webhook_metric:
            widgets.update(webhook_metric)
        boto3.client('sqs').delete_message(
            QueueUrl=os.environ['queue_url'],
            ReceiptHandle=event['Records'][0]['receiptHandle']
        )
    else:
        print("Updating widgets for an EventBridge event")
        widgets.update(create_and_put_metrics_and_widgets())

    if widgets:
        cw_interactions.create_or_update_dashboard(widgets)
    else:
        print('No valid widgets, dashboard cannot be created.')


def create_and_put_metrics_and_widgets() -> dict:
    """For each repository, aggregates all text and metric data and creates widgets for each

    :returns: a dictionary mapping the dashboard name to the list of the text and metric widgets for each repository to
              put in the dashboard
    :rtype: dict
    """
    widgets = {}
    for repo_name in os.environ['repo_names'].split(','):
        owner = os.environ['owner']
        if '/' in repo_name:
            [owner, repo_name] = repo_name.split('/')

        sorted_widgets = github_docker.aggregate_metrics(owner, repo_name)
        # Create a Cloudwatch metric/text widget out of each sorted widget
        for widget_title, widget in sorted_widgets.items():
            if widget['type'] == 'metric':
                title = repo_name
                if widget_title != os.environ['default_metric_widget_name']:
                    title += ' ' + widget_title
                formatted_widget = cw_interactions.create_metric_widget(repo_name, widget['data'], title)
            elif widget['type'] == 'text':
                title = repo_name
                if widget_title == os.environ['default_text_widget_name']:
                    title += ' Properties'
                else:
                    title += ' ' + widget_title
                formatted_widget = cw_interactions.create_text_widget(widget['data'], title=title)
            else:
                print("Invalid widget type specified for widget:", widget_title)
                continue

            dashboard_name = os.environ['dashboard_name_prefix']
            if widget['dashboard_level'] != 'main':
                dashboard_name += '-' + repo_name

            # Add widgets to dashboard
            widgets_for_specified_dashboard = widgets.get(dashboard_name, [])
            widgets_for_specified_dashboard.append(formatted_widget)
            widgets[dashboard_name] = widgets_for_specified_dashboard

        # Add activity widget
        main_widgets = widgets.get(os.environ['dashboard_name_prefix'], [])
        main_widgets.append(cw_interactions.create_activity_widget(repo_name))
        widgets[os.environ['dashboard_name_prefix']] = main_widgets

    return widgets
