import argparse
import json
import sys
import subprocess

from colorama import Fore
from termcolor import colored


def print_header(content: str):
    """Prints the content bolded and in magenta

    :param: the content to print
    :type: str
    """
    print(colored(Fore.MAGENTA + content + Fore.RESET, attrs=['bold']))


def print_section_header(content: str):
    """Prints the content underlined

    :param: the content to print
    :type: str
    """
    print(colored('\n' + content, attrs=['underline']))


def print_green(content: str):
    """Prints the content in green

    :param: the content to print
    :type: str
    """
    print(Fore.GREEN + content + Fore.RESET)


def print_yellow(content: str):
    """Prints the content in yellow

    :param: the content to print
    :type: str
    """
    print(Fore.YELLOW + content + Fore.RESET)


def print_blue(content: str):
    """Prints the content in blue

    :param: the content to print
    :type: str
    """
    print(Fore.BLUE + content + Fore.RESET)


def print_red(content: str):
    """Prints the content in red

    :param: the content to print
    :type: str
    """
    print(Fore.RED + content + Fore.RESET)


def print_cyan(content: str):
    """Prints the content in cyan

    :param: the content to print
    :type: str
    """
    print(Fore.CYAN + content + Fore.RESET)


def check_interactive() -> bool:
    """Checks the --d flag to see if the launch script should be interactive or not

    :returns: a boolean that represents whether the launch script should be interactive or not
    :rtype: bool
    """
    parser = argparse.ArgumentParser(description='Argument parser for launch.py')
    parser.add_argument('--d', action='store_true', help='This flag disables interactive mode')
    return not parser.parse_args().d


def get_context_variables(context_vars: list) -> dict:
    """Retrieves the context variables from the `configuration/config_variables.json` file

    :param context_vars: a list of all the context variable names
    :type context_vars: list
    :returns: the dictionary containing the entire cdk.json file and the dictionary containing just the context variables
    :rtype: dict
    """
    with open('configuration/config_variables.json') as json_file:
        variables = json.load(json_file)

    if not isinstance(variables, dict):
        raise RuntimeError('Incorrectly formatted configuration/config_variables.json file.')

    for context_var in context_vars:
        if context_var not in variables.keys():
            raise RuntimeError('Incorrectly formatted configuration/config_variables.json file.')

    return variables


def config_widgets() -> tuple:
    """Configures the default widgets, the metrics that belong to them, and the dashboard level they're

    :return: a tuple of the dictionary representing the widgets, the default metric widget name, and the default text widget name
    :rtype: tuple
    """
    default_metric_widget_name = 'details-open-source-dashboard-default-metric-widget-title-do-not-modify'
    default_text_widget_name = 'main-open-source-dashboard-default-metric-text-title-do-not-modify'
    widgets = {
        'Repository Status': {
            'dashboard_level': 'main',
            'type': 'metric',
            'metrics': ['stargazers_count', 'forks_count', 'open_issues_count', 'pulls', 'contributors']
        },
        default_text_widget_name: {
            'dashboard_level': 'main',
            'type': 'text',
            'metrics': ['releases/latest/tag_name', 'tags/results*0*name', 'tags/results*0*images*0*architecture']
        },
        default_metric_widget_name: {
            'dashboard_level': 'details',
            'type': 'metric',
            'metrics': ['subscribers_count', 'pull_count', 'tags/results*0*full_size',
                        'community/profile/health_percentage']
        },
        'Outliers': {
            'dashboard_level': 'details',
            'type': 'text',
            'metrics': ['issues?sort=created&direction=asc/0*title', 'issues?sort=created&direction=asc/0*updated_at',
                        'pulls?sort=updated/0*title', 'pulls?sort=updated/0*updated_at']
        },
        'Popularity': {
            'dashboard_level': 'details',
            'type': 'metric',
            'metrics': ['traffic/clones/uniques', 'traffic/views/uniques']
        }
    }
    return json.dumps(widgets), default_metric_widget_name, default_text_widget_name


def update_context_variables(variables: dict):
    """Updates the list of context variables in `cdk.json` according to user input

    :param variables: the content of the 'context' entry in the data dictionary
    :type variables: dict
    """
    with open('configuration/config_variables.json', 'w') as json_file:
        json.dump(variables, json_file, indent=4)

    with open('cdk.json') as json_file:
        data = json.load(json_file)

    with open('cdk.json', 'w') as json_file:
        for name, value in variables.items():
            if isinstance(value, dict):
                variables[name] = json.dumps(value)
        data['context'].update(variables)
        json.dump(data, json_file, indent=4)


def run_command(command: str, capture_output: bool, print_command=True,
                print_success=True) -> subprocess.CompletedProcess:
    """Runs the specified command-line command

    :param command: the command to run
    :type command: str
    :param capture_output: whether to capture the stdout/stderr output of the command or let it show up in the terminal
    :type capture_output: bool
    :param print_command: whether to print the command
    :type print_command: bool
    :param print_success: whether to print the command success
    :type print_success: bool
    :returns: the completed subprocess
    :rtype: subprocess.CompletedProcess
    """
    if print_command:
        print_cyan('\t' + command)

    completed_process = subprocess.run(command.split(' '), capture_output=capture_output)
    if completed_process.returncode != 0:
        try:
            if not print_command:
                print("'" + command + "' failed. Error:")
            print(completed_process.stderr.decode('utf-8'))
        except AttributeError:
            print_red('The error message could not be decoded')

        print_red('\nCould not complete task successfully. Terminating launch.')
        sys.exit()

    if print_success:
        print_green('\tTask completed successfully')

    return completed_process


def create_or_update_secret(github_token: str):
    """Creates or updates a secret in AWS SecretsManager containing the github token

    :param github_token: the GitHub personal authentication token
    :type github_token: str
    """
    list_secrets_command = 'aws secretsmanager list-secrets'
    list_secrets = run_command(list_secrets_command, True, print_command=False, print_success=False)

    if 'github_auth_token' in list_secrets.stdout.decode('utf-8'):
        secret_command = 'aws secretsmanager put-secret-value --secret-id github_auth_token --secret-string ' + github_token
    else:
        secret_command = 'aws secretsmanager create-secret --name github_auth_token --secret-string ' + github_token
    print('\nCreating or updating AWS Secret Manager secret for GitHub token 🤐 🤐 🤐')
    run_command(secret_command, True)


def synthesize(github_token: str):
    """Synthesizes the CloudFormation template

    :param github_token: the GitHub personal authentication token
    :type github_token: str
    """
    synth_command = 'cdk synth -c github_token=' + github_token
    print('\nSynthesizing CloudFormation template ☁️☁️☁️')
    run_command(synth_command, True)


def bootstrap(github_token: str):
    """Deploys the bootstrap stack

    :param github_token: the GitHub personal authentication token
    :type github_token: str
    """
    bootstrap_command = 'cdk bootstrap -c github_token=' + github_token
    print('\nBootstrapping stack 👢👢👢')
    run_command(bootstrap_command, True)


def deploy(github_token: str):
    """Deploys the RepositoryStatusMonitorStack

    :param github_token: the GitHub personal authentication token
    :type github_token: str
    """
    deploy_command = 'cdk deploy -c github_token=' + github_token
    print('\nDeploying stack 🥞🥞🥞')
    run_command(deploy_command, False, print_success=False)
    print('\n 🎉🎉🎉 Stack successfully deployed 🎉🎉🎉')


def invoke_webhook_creator():
    """Invokes the WebhookCreator Lambda function"""
    invoke_lambda_command = 'aws lambda invoke --function-name WebhookCreator response.json'
    print('\nCreating GitHub webhooks 🎣 🎣 🎣 ')
    run_command(invoke_lambda_command, True)
    run_command('rm response.json', True, print_command=False, print_success=False)


def verify_context_variables(variables: dict, context_variables: list, non_empty_context_vars: list, questions: dict,
                             config_values: list) -> dict:
    """Presents the context variables to the user for approval and updates them in `cdk.json` accordingly

    :param variables: the context variables and their default values
    :type variables: dict
    :param context_variables: the keys of the context variables
    :type context_variables: list
    :param non_empty_context_vars: the context variables that must have values specified
    :type non_empty_context_vars: list
    :param questions: the customized question to use when asking the user for approval of each context variable
    :type questions: dict
    :param config_values: the context variables that are specified as dictionaries not strings
    :type config_values: list
    :returns: the dictionary containing the updated context variables
    :rtype: dict
    """
    for param_name in context_variables:
        if param_name == 'docker_fields' and variables['get_docker'] == 'n':
            continue

        print_blue("\nContext Variable: " + param_name)
        param_value = variables[param_name]
        if param_name == 'dashboard_name_prefix':
            exists, dash_prefix = check_if_dashboard_prefix_taken(param_value)
            if exists:
                variables[param_name] = dash_prefix
                continue

        if param_value and param_value != "":
            if isinstance(param_value, str):
                print(questions[param_name] % (param_value), "(y/n)")
            else:
                print(questions[param_name], " (y/n)")
                for name, value in param_value.items():
                    print(name + ':', value)

            approval = input_wrapper()
        else:
            print("There is no default value for", param_name + '.')
            approval = "n"

        while not approval or not (approval == 'y' or approval == 'n'):
            print_yellow("You must choose whether or not to approve the value. Type 'y' for approval, 'n' otherwise.")
            approval = input_wrapper()

        if approval == 'n':
            if param_name in config_values:
                print('Add values or edit/delete existing values in the configuration/config_variables.json file and' +
                      'run this launch script again. Your progress will not be saved.')
                sys.exit()
            print('Please specify a new value for',
                  param_name + '. Refer to the README for an example of the required format.')
            new_value = input_wrapper()

            if param_name in non_empty_context_vars:
                while not new_value:
                    print_yellow('You must input a new value for ' + param_name + '.')
                    new_value = input_wrapper()

            if param_name == 'dashboard_name_prefix':
                exists, new_name = check_if_dashboard_prefix_taken(new_value)
                if exists:
                    new_value = new_name

            variables[param_name] = new_value
            print_green('New value for ' + param_name + ' is ' + "'" + new_value + "'.")
        else:
            print_green(param_name + ' confirmed!')

    return variables


def check_if_dashboard_prefix_taken(dashboard_name_prefix: str) -> tuple:
    """Checks whether dashboards that have the same prefix as the 'dashboard_name_prefix' context variable already exists

    :param dashboard_name_prefix: the 'dashboard_name_prefix' context variable
    :type dashboard_name_prefix: str
    :returns: a boolean of whether the dashboard exists and its name
    :rtype: tuple
    """
    if not dashboard_name_prefix:
        return False, ""

    print('The specified dashboard name prefix is', "'" + dashboard_name_prefix + "'")
    already_exists, existing_dashboard_names = dashboard_already_exists(dashboard_name_prefix)
    if not already_exists:
        return False, ""

    print('Do you wish to choose a new prefix, delete the existing dashboards, or import data from the existing ' +
          'dashboards? (new/delete/import)')
    dash_approval = input_wrapper()

    while True:
        if dash_approval == 'new':
            print('Please type the new dashboard name prefix now.')
            new_prefix = input_wrapper()
            while new_prefix == "":
                print('You must input a new dashboard name prefix.')
                new_prefix = input_wrapper()

            already_exists, existing_dashboard_names = dashboard_already_exists(new_prefix)
            if not already_exists:
                return True, new_prefix
            print('Do you wish to choose a new prefix, delete the existing dashboards, or import data from ' +
                  'the existing dashboards? (new/delete/import)')
            dash_approval = input_wrapper()
            continue
        elif dash_approval == 'delete':
            delete_main_and_details_dashboards(existing_dashboard_names)
            return True, dashboard_name_prefix
        elif dash_approval == 'import':
            print('You have chosen to import the data from the existing dashboards. ' +
                  'Non-conflicting widgets will be imported from all dashboards.')
            return True, dashboard_name_prefix

        print_yellow("You must choose either 'new', 'delete', or 'import'.")
        dash_approval = input_wrapper()


def dashboard_already_exists(dashboard_name_prefix: str) -> tuple:
    """Retrieve and return existing dashboards

    :param dashboard_name_prefix: the 'dashboard_name_prefix' context variable
    :type dashboard_name_prefix: str
    :returns: a tuple of a boolean of whether the dashboard exists and the existing dashboards' names 
    :rtype: tuple
    """
    print('Checking whether dashboard name prefix is already taken ...')
    list_dashboards_command = 'aws cloudwatch list-dashboards --dashboard-name-prefix ' + dashboard_name_prefix
    list_dashboards = run_command(list_dashboards_command, True, print_command=False, print_success=False)
    dashboards = json.loads(list_dashboards.stdout.decode('utf-8'))['DashboardEntries']

    if not dashboards:
        print_green('Prefix is available. No conflict.')
        return False, []

    existing_dashboard_names = [dashboard['DashboardName'] for dashboard in dashboards]
    print_red('Prefix' + " '" + dashboard_name_prefix + "' " + 'already taken.')
    print_red('Existing dashboards with prefix are: ' + ', '.join(existing_dashboard_names))
    return True, existing_dashboard_names


def delete_main_and_details_dashboards(existing_dashboards):
    """Delete specified dashboards

    :param existing_dashboards: the dashboards to delete
    :type existing_dashboards: list
    """
    print('You have chosen to delete the existing dashboards. Deleting the dashboards now ...')
    delete_command = 'aws cloudwatch delete-dashboards --dashboard-names ' + ' '.join(existing_dashboards)
    run_command(delete_command, True, print_command=False, print_success=False)
    print_green('Delete successful.')


def get_github_token() -> str:
    """Gets the GitHub personal authentication from the user

    :returns: the GitHub token
    :rtype: str
    """
    print_blue('\nPlease input your GitHub personal access token.')
    github_token = input_wrapper()
    while not github_token:
        print_yellow('You must input your GitHub personal access token.')
        github_token = input_wrapper()

    return github_token


def input_wrapper() -> str:
    """Wrap the input() command to add a consistent prompt icon"""
    return input('> ')
