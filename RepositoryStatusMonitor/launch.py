#! /usr/bin/env python3

from colorama import init as colorama_init

import launch_functions as lf

colorama_init()

lf.print_header("*** LAUNCHING OPEN SOURCE DASHBOARD ***")

interactive = lf.check_interactive()

context_vars = ['owner', 'repo_names', 'get_docker', 'github_fields_unpaginated', 'github_fields_paginated',
                'docker_fields', 'dashboard_name_prefix']
interactive_questions = {
    "owner": "Is the correct GitHub owner of your repositories '%s'?",
    "get_docker": "Your current decision on whether to collect DockerHub metrics is '%s'. Is this still correct?",
    "repo_names": "Are these the correct repositories?\n%s",
    "github_fields_unpaginated": "Are these the correct unpaginated metrics to collect from GitHub?",
    "github_fields_paginated": "Are these the correct paginated metrics to collect from GitHub?",
    "docker_fields": "Are these the correct metrics to retrieve from DockerHub?",
    "dashboard_name_prefix": "Is the correct prefix for all dashboard names '%s'?"
}
non_empty_context_vars = ['repo_names', 'get_docker', 'dashboard_name_prefix']
config_values = ['github_fields_unpaginated', 'github_fields_paginated', 'docker_fields']
variables = lf.get_context_variables(context_vars)
if interactive:
    lf.print_section_header("CONFIRMING CONTEXT VARIABLES ... ")
    variables = lf.verify_context_variables(variables, context_vars, non_empty_context_vars, interactive_questions,
                                            config_values)

    widgets, default_metric_widget_name, default_text_widget_name = lf.config_widgets()
    variables['widgets'] = widgets
    variables['default_metric_widget_name'] = default_metric_widget_name
    variables['default_text_widget_name'] = default_text_widget_name
    lf.update_context_variables(variables)
    print("\nContext variables updated successfully!")  

lf.print_section_header("RETRIEVING GITHUB TOKEN ... ")
github_token = lf.get_github_token()

lf.create_or_update_secret(github_token)

lf.print_section_header("SYNTHESIZING CLOUDFORMATION TEMPLATE ... ")
lf.synthesize(github_token)

lf.print_section_header("CREATING BOOTSTRAP STACK ... ")
lf.bootstrap(github_token)

lf.print_section_header("DEPLOYING OPEN SOURCE DASHBOARD STACK ... ")
lf.deploy(github_token)

lf.print_section_header("CREATING WEBHOOKS ... ")
lf.invoke_webhook_creator()
