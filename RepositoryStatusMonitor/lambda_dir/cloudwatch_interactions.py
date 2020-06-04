from datetime import datetime, timezone, timedelta
import json
import math
import os
import re

import boto3

cloudwatch = boto3.client('cloudwatch')


def create_or_update_dashboard(dashboard_widget_mapping: dict):
    """Creates or updates the specified dashboard with the specified widgets

    :param dashboard_widget_mapping: a mapping of the dashboard name to the widgets to create/update that dashboard with
    :type dashboard_widget_mapping: dict
    """
    for dashboard_name, widgets_to_put in dashboard_widget_mapping.items():
        existing_dashboards = cloudwatch.list_dashboards(
            DashboardNamePrefix=dashboard_name
        )
        existing_widgets = []
        for dashboard in existing_dashboards['DashboardEntries']:
            if dashboard['DashboardName'] == dashboard_name:
                existing_widgets = json.loads(cloudwatch.get_dashboard(DashboardName=dashboard_name)['DashboardBody'])[
                    'widgets']

        for widget in widgets_to_put:
            match = None
            if widget['type'] == 'metric':
                for ew in existing_widgets:
                    if ew['type'] != 'text' and widget['properties']['title'] == ew['properties']['title']:
                        match = ew
            elif widget['type'] == 'text':
                title = re.search(r'#\s(.*?)\n', widget['properties']['markdown']).groups()[0]
                for ew in existing_widgets:
                    if ew['type'] == 'text' and title in ew['properties']['markdown']:
                        match = ew
            if match:
                existing_widgets.remove(match)

        widgets_to_put.extend(existing_widgets)

        try:
            print("Populating dashboard " + dashboard_name + " with the following widgets")
            print(widgets_to_put)
            cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps({'widgets': widgets_to_put})
            )
        except cloudwatch.exceptions.DashboardInvalidInputError:
            print("Failed to create dashboard. Dashboard input invalid")
        except:
            print("Failed to create dashboard. Unexpected error occurred")


def create_metric_widget(repo_name: str, metric_data: dict, title: str, view='singleValue', id_str=None,
                         granularity=None) -> dict:
    """Creates a new metric widget

    :param repo_name: the name of the repository to use as a dimension of the metric
    :type repo_name: str
    :param metric_data: the metric data to create a widget with
    :type metric_data: dict
    :param title: the title of the widget
    :type title: str
    :param view: whether the widget should show single values or a time-series graph (default is "singleValue)
    :type view: str
    :param id_str: the id of the metric (used when the widget shows an expression of the metric, not the metric itself)
    :type id_str: str
    :param granularity: the granularity to use for the expression (used in metric expression)
    :type granularity: str
    :returns: the dictionary representing the widget
    :rtype: dict
    """
    if not repo_name:
        print("failed to create metric widget. No repo_name provided")
        return {}
    if not metric_data:
        print("failed to create metric widget. No metric_data provided")
        return {}

    print("creating metric widget " + title + " for " + repo_name)

    cloudwatch_metrics = []
    widget_metric_data = []
    namespace = os.environ['namespace']
    for metric_name, metric_value in metric_data.items():
        cloudwatch_metrics.append(new_metric(repo_name, metric_name, metric_value))

        if not id_str or granularity not in ['minutes', 'hours', 'days']:
            widget_metric_data.append([namespace, metric_name, 'REPO_NAME', repo_name])
        else:
            denominator = {'minutes': '(60)', 'hours': '(3600)', 'days': '(3600*24)'}
            suffix = {'minutes': ' (in minutes)', 'hours': ' (in hours)', 'days': ' (in days)'}
            widget_metric_data.append(
                [namespace, metric_name, 'REPO_NAME', repo_name, {"id": id_str, "visible": False}])
            widget_metric_data.append([{'expression': id_str + '/' + denominator[granularity],
                                        'label': metric_name + suffix[granularity], "id": id_str + "Expression"}])

    put_metrics_in_cloudwatch(cloudwatch_metrics)

    rows = math.ceil(len(metric_data) / 3)
    return {
        'type': 'metric',
        'width': 6,
        'height': rows * 3,
        'properties': {
            'metrics': widget_metric_data,
            'view': view,
            'period': 3600,
            'stat': 'Maximum',
            'region': os.environ['AWS_REGION'],
            'title': title
        }
    }


def create_text_widget(text_data: dict, title: str) -> dict:
    """Creates a new text widget with the specified data

    :param text_data: the metric data to put in the widget
    :type text_data: dict
    :param title: the title of the widget
    :type title: str
    :returns: the dictionary representing the widget
    :rtype: dict
    """
    if not title or not text_data or not isinstance(text_data, dict):
        print("failed to create a text widget. Missing parameters")
        return {}

    text_widget_string = '## ' + title + '\n Name | Value \n ----|----- \n'
    for metric_name, metric_text in text_data.items():
        text_widget_string += metric_name + ' | ' + metric_text + '\n'

    # Keep height of text widget closer to height of content (makes height more responsive)
    height = 2 + (math.ceil(len(text_data) / 3) * 2 if math.floor(len(text_data) / 3) >= 1 else 2)
    return {
        'type': 'text',
        'height': height,
        'properties': {
            'markdown': text_widget_string
        }
    }


def new_metric(repo_name: str, metric_name: str, metric_value: float) -> dict:
    """Creates a new metric in the format required for CloudWatch

    :param repo_name: the repository name to associate with the metric
    :type repo_name: str
    :param metric_name: the name of the metric
    :type metric_name: str
    :param metric_value: the value of the metric
    :type metric_value: int
    :returns: the dictionary representing the metric
    :rtype: dict
    """
    if not metric_name or not repo_name:
        print("Not creating new metric: missing metric/repo name")
        return {}

    if not isinstance(metric_value, (int, float)):
        if not isinstance(metric_value, str) or not metric_value.isnumeric():
            print("Not creating new metric: metric value is an invalid type")
            return {}
        metric_value = float(metric_value)

    return {
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


def put_metrics_in_cloudwatch(cloudwatch_metrics: list):
    """Puts the specified metrics in CloudWatch

    :param cloudwatch_metrics: the metric data to put in CloudWatch
    :type cloudwatch_metrics: dict
    """
    cloudwatch.put_metric_data(
        Namespace=os.environ['namespace'],
        MetricData=cloudwatch_metrics
    )


def create_activity_widget(repo_name):
    """Creates a widget displaying the repository activity over the last 24 hours

    :param repo_name: the repository to create the widget for
    :type repo_name: str
    :returns: a widget representing the activity data
    :rtype: dict
    """
    namespace = os.environ['namespace']
    metric_names = [
        'PRs Merged',
        'PRs Closed',
        'PRs Opened',
        'Issues Closed',
        'Issues Opened',
        'Releases Published',
        'Pushes to Master'
    ]
    metric_data_queries = []
    for index in range(len(metric_names)):
        metric_name = metric_names[index]
        metric_data_queries.append(
            {
                'Id': 'm' + str(index),
                'MetricStat': {
                    'Metric': {
                        'Namespace': namespace,
                        'MetricName': metric_name,
                        'Dimensions': [
                            {
                                'Name': 'REPO_NAME',
                                'Value': repo_name
                            },
                        ]
                    },
                    'Period': 60,
                    'Stat': 'Maximum'
                }
            }
        )
    response = cloudwatch.get_metric_data(
        MetricDataQueries=metric_data_queries,
        StartTime=datetime.now(timezone.utc) - timedelta(days=1),
        EndTime=datetime.now(timezone.utc)
    )
    for result in response['MetricDataResults']:
        if not result['Values']:
            put_metrics_in_cloudwatch([new_metric(repo_name, result['Label'], 0)])

    widget_metric_data = [[namespace, metric_name, 'REPO_NAME', repo_name] for metric_name in metric_names]

    return {
        'type': 'metric',
        'width': 6,
        'height': math.ceil(len(widget_metric_data) / 3) * 3,
        'properties': {
            'metrics': widget_metric_data,
            'view': 'singleValue',
            'period': 3600 * 24,
            'stat': 'Sum',
            'region': os.environ['AWS_REGION'],
            'title': repo_name + ' Activity Over the Last 24 hours'
        }
    }