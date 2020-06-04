from sys import stderr

from aws_cdk import (
    aws_apigateway as apigw,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_lambda_event_sources as lambda_event_source,
    aws_sqs as sqs,
    core
)

from lambda_dir import http_handler as hh

class RepositoryStatusMonitorStack(core.Stack):
    """
    A class used to represent an AWS CloudFormation stack.
    ...

    Methods
    -------
    create_role_and_policy()
        Creates an AWS IAM role, attaches a custom policy to it, and returns the role
    create_event_with_permissions(lambda_function: _lambda.Function)
        Creates an AWS EventBridge rule and attaches the AWS Lambda function parameter as a target
    handle_parameters()
        Retrieves all context variables, checks for valid input, performs all necessary processing, and returns a dictionary of the processed variables
    validate_repo_names(repo_names: str)
        Retrieves the list of GitHub repositories to which the user has access and validates that all repositories specified for the dashboard exist in that list
    """

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        """Initializes the stack

        :param scope: parent of this stack, scope within which resources defined here are accessible
        :type file_loc: Optional[aws_cdk.core.Construct]
        :param id: the id of the stack
        :type id: Optional[str]
        :param **kwargs: additional optional arguments
            ``description``:
                a description of the stack (`Optional[str]`).
            ``env``
                AWS environment (account/region) where this stack will be deployed (`Optional[aws_cdk.core.Environment]`).
            ``stack_name``
                name with which to deploy the stack (`Optional[str]`).
            ``synthesizer``
                synthesis method to use while deploying this stack (`Optional[aws_cdk.core.IStackSynthesizer]`).
            ``tags``
                stack tags that will be applied to all taggable resources as well as the stack (`Optional[Mapping[str, str]]`).
            ``termination_protection``
                whether to enable termination protection for this stack (`Optional[bool]`).
        """
        super().__init__(scope, id, **kwargs)
        metric_handler_dict, webhook_creator_dict = self.handle_parameters()

        dead_letter_queue = sqs.Queue(
            self, 'DeadLetterQueue',
            queue_name='DeadLetterQueue'
        )
        webhook_queue = sqs.Queue(
            self, 'WebhookQueue',
            queue_name='WebhookQueue',
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3, 
                queue=dead_letter_queue)
        )
        metric_handler_dict['queue_url'] = webhook_queue.queue_url

        metric_handler_management_role = self.create_lambda_role_and_policy(
            'MetricHandlerManagementRole', 
            [   
                'cloudwatch:GetDashboard',
                'cloudwatch:GetMetricData',
                'cloudwatch:ListDashboards',
                'cloudwatch:PutDashboard',
                'cloudwatch:PutMetricData',
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents',
                'secretsmanager:GetSecretValue'
            ]
        )
        metric_handler_timeout = int(self.node.try_get_context('lambda_timeout')) if self.node.try_get_context('lambda_timeout') else 300
        metric_handler_function = _lambda.Function(
            self, 'MetricsHandler',
            function_name='MetricsHandler',
            runtime=_lambda.Runtime.PYTHON_3_7,
            code=_lambda.Code.asset('lambda_dir'),
            handler='cloudwatch_dashboard_handler.handler',
            role=metric_handler_management_role,
            environment=metric_handler_dict,
            timeout=core.Duration.seconds(metric_handler_timeout)
        )
        self.create_event_with_permissions(metric_handler_function)

        # Connect SQS to Lambda
        sqs_event_source = lambda_event_source.SqsEventSource(webhook_queue)
        metric_handler_function.add_event_source(sqs_event_source)

        apigw_webhook_url = self.create_and_integrate_apigw(webhook_queue, metric_handler_dict['dashboard_name_prefix'])
        webhook_creator_dict['apigw_endpoint'] = apigw_webhook_url

        webhook_role = self.create_lambda_role_and_policy('WebhookCreatorRole',['secretsmanager:GetSecretValue'])
        webhook_function = _lambda.Function(
            self, 'WebhookCreator',
            function_name='WebhookCreator',
            runtime=_lambda.Runtime.PYTHON_3_7,
            code=_lambda.Code.asset('lambda_dir'),
            handler='webhook_creator.handler',
            role=webhook_role,
            environment=webhook_creator_dict,
            timeout=core.Duration.seconds(5)
        )

    def create_lambda_role_and_policy(self, name: str, actions: list) -> iam.Role:
        """Creates an AWS IAM role, attaches a managed and a custom policy to it, and returns the role 

        :param name: the name and ID of the role
        :type name: str
        :param actions: the actions that the Lambda role can execute
        :type actions: list
        :returns: a role with a custom and a managed policy attached
        :rtype: aws_cdk.aws_iam.Role
        """
        role = iam.Role(self, name,
                        role_name=name,
                        assumed_by=iam.ServicePrincipal(
                            'lambda.amazonaws.com'),
                        managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name(
                            'service-role/AWSLambdaBasicExecutionRole')]
                        )

        role.add_to_policy(iam.PolicyStatement(
            resources=['*'],
            actions=actions
        ))
        return role

    def create_event_with_permissions(self, lambda_function: _lambda.Function) -> None:
        """Creates an AWS EventBridge rule and attaches the AWS Lambda function parameter as a target

        :param lambda_function: the AWS Lambda function for which to create the rule
        :type lambda_function: aws_cdk.aws_lambda.Function
        """
        hourly_metric_retrieval_rule = events.Rule(
                self, 'Rule',
                rule_name='HourlyMetricRetrieval',
                enabled=True,
                schedule=events.Schedule.expression('rate(1 hour)')
            )
        hourly_metric_retrieval_rule.add_target(targets.LambdaFunction(lambda_function))


    def handle_parameters(self) -> tuple:   
        """Retrieves all context variables, checks for valid input, performs all necessary processing, and returns a dictionary of the processed variables

        :returns: a tuple containing two dictionaries, each containing all the processed context variables for each Lambda function
        :rtype: tuple
        """ 
        repo_names_unvalidated = self.node.try_get_context('repo_names')
        docker_bool = self.node.try_get_context('get_docker')
        dashboard_name_prefix = self.node.try_get_context('dashboard_name_prefix')
        owner = self.node.try_get_context('owner')
        github_fields_paginated = self.node.try_get_context('github_fields_paginated') if self.node.try_get_context('github_fields_paginated') is not None else ""
        github_fields_unpaginated = self.node.try_get_context('github_fields_unpaginated') if self.node.try_get_context('github_fields_unpaginated') is not None else ""
        docker_fields = self.node.try_get_context('docker_fields') if self.node.try_get_context('docker_fields') is not None else ""
        namespace = self.node.try_get_context('namespace')
        user_agent_header = self.node.try_get_context('user_agent_header')
        widgets = self.node.try_get_context('widgets') if self.node.try_get_context('widgets') is not None else ""
        default_metric_widget_name = self.node.try_get_context('default_metric_widget_name')
        default_text_widget_name = self.node.try_get_context('default_text_widget_name')

        if self.node.try_get_context('github_token') is None or self.node.try_get_context('github_token') == "":
            raise ValueError('Need to specify GitHub token.')
        if repo_names_unvalidated is None or repo_names_unvalidated == "":
            raise ValueError('Need to specify repository names.')
        if dashboard_name_prefix is None or dashboard_name_prefix == "":
            raise ValueError('Need to specify prefix for dashboard names.')
        if docker_bool is None or docker_bool == "":
            raise ValueError('Need to specify whether to include docker metrics.')
        if owner is None:
            raise ValueError('Need to specify GitHub owner.')
        if namespace is None or namespace == "":
            raise ValueError('Need to specify namespace for CloudWatch metrics.')
        if user_agent_header is None or user_agent_header == "":
            raise ValueError('Need to specify User-Agent header for GitHub requests.')
        if default_metric_widget_name is None or default_metric_widget_name == "":
            raise ValueError('Need to specify default metric widget name.')
        if default_text_widget_name is None or default_text_widget_name == "":
            raise ValueError('Need to specify default text widget name.')

        repo_names = self.validate_repo_names(repo_names_unvalidated, owner, user_agent_header)

        metric_handler_dict = {
            'repo_names': repo_names,
            'docker_bool': docker_bool, 
            'dashboard_name_prefix': dashboard_name_prefix,
            'github_fields_unpaginated': github_fields_unpaginated,
            'github_fields_paginated': github_fields_paginated,
            'docker_fields': docker_fields,
            'owner': owner,
            'namespace': namespace,
            'user_agent_header': user_agent_header,
            'widgets': widgets,
            'default_metric_widget_name': default_metric_widget_name,
            'default_text_widget_name': default_text_widget_name
        }

        webhook_creator_dict = {
            'repo_names': repo_names, 
            'owner': owner,
            'user_agent_header': user_agent_header
        }

        return metric_handler_dict, webhook_creator_dict
        

    def validate_repo_names(self, repo_names: str, owner: str, user_agent_header: str) -> str:
        """Retrieves the list of GitHub repositories to which the user has access and validates that all repositories specified for the dashboard exist in that list

        :param repo_names: the repository names passed in as context variables
        :type repo_names: str
        :param owner: the GitHub owner of the repositories
        :type owner: str
        :param user_agent_header: the User-Agent header for GitHub requests
        :type user_agent_header: str
        :returns: the repository names that exist for the user in GitHub
        :rtype: str
        """ 
        headers = {'Authorization': 'token ' + self.node.try_get_context('github_token'),
                   'Accept': 'application/vnd.github.nebula-preview+json',
                   'User-Agent': user_agent_header}
        url = 'https://api.github.com/user/repos'
        success, data, response_headers = hh.request_handler(url, headers=headers)
        if not success:
            raise RuntimeError(data['message'])

        existing_repos = set()
        for repo in data:
            existing_repos.add(repo['full_name'])

        valid_names = []
        invalid_names = []
        for repo_name in repo_names.split(','):
            if '/' not in repo_name:
                repo_name = owner + '/' + repo_name

            if repo_name not in existing_repos:
                invalid_names.append(repo_name)
            else:
                valid_names.append(repo_name)

        if len(invalid_names) > 0:
            invalid_repos = ', '.join(invalid_names)
            valid_repos = "none" if not valid_names else ', '.join(valid_names)
            print('Invalid repositories: ' + invalid_repos, file=stderr)
            print('Valid repositories: ' + valid_repos, file=stderr)
            raise RuntimeError("All repository names must be valid.")

        return ','.join(valid_names)


    def create_and_integrate_apigw(self, queue: sqs.Queue, dashboard_name_prefix: str) -> str:
        """Creates API Gateway and integrates with SQS queue

        :param queue: the SQS queue to integrate with
        :type queue: aws_cdk.aws_sqs.Queue
        :param dashboard_name_prefix: the dashboard name to use as the API Gateway resource name
        :type dashboard_name_prefix: str
        :returns: the url that the webhooks will post to
        :rtype: str
        """ 
        webhook_apigw_role = iam.Role(
            self,
            'WebhookAPIRole',
            role_name='WebhookAPIRole',
            assumed_by=iam.ServicePrincipal('apigateway.amazonaws.com')
        )
        webhook_apigw_role.add_to_policy(iam.PolicyStatement(
            resources=['*'],
            actions=[
                'sqs:SendMessage'
            ]
        ))

        webhook_apigw = apigw.RestApi(self, 'RepositoryStatusMonitorAPI', rest_api_name='RepositoryStatusMonitorAPI')
        webhook_apigw_resource = webhook_apigw.root.add_resource(dashboard_name_prefix)

        apigw_integration_response = apigw.IntegrationResponse(
            status_code='200',
            response_templates={'application/json': ""}
        )
        apigw_integration_options = apigw.IntegrationOptions(
            credentials_role=webhook_apigw_role,
            integration_responses=[apigw_integration_response],
            request_templates={'application/json': 'Action=SendMessage&MessageBody=$input.body'},
            passthrough_behavior=apigw.PassthroughBehavior.NEVER,
            request_parameters={'integration.request.header.Content-Type': "'application/x-www-form-urlencoded'"}
        )
        webhook_apigw_resource_sqs_integration = apigw.AwsIntegration(
            service='sqs',
            integration_http_method='POST',
            path='{}/{}'.format(core.Aws.ACCOUNT_ID, queue.queue_name),
            options=apigw_integration_options
        )

        webhook_apigw_resource.add_method(
            'POST',
            webhook_apigw_resource_sqs_integration,
            method_responses=[apigw.MethodResponse(status_code='200')]
        )

        path = '/' + dashboard_name_prefix
        return webhook_apigw.url_for_path(path)
