#!/usr/bin/env python3
import os
import json 

from aws_cdk import core

from repository_status_monitor_stack import RepositoryStatusMonitorStack

app = core.App()

with open('configuration/environment_config.json') as json_file:
    environment = json.load(json_file)
    region = environment['region'] if environment['region'] != "" else os.environ['CDK_DEFAULT_REGION']
    account = environment['account'] if environment['account'] != "" else os.environ['CDK_DEFAULT_ACCOUNT']
rsm_stack = RepositoryStatusMonitorStack(app, 'RepositoryStatusMonitor', env=core.Environment(account=account, region=region))

core.Tag.add(rsm_stack, 'OpenSourceDashboard', app.node.try_get_context('dashboard_name_prefix'))

app.synth()
