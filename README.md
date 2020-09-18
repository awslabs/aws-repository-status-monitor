# AWS Repository Status Monitor
The AWS Repository Status Monitor helps open-source developers keep track of GitHub and Docker metrics for their open source projects.
An AWS Lambda function, triggered hourly, consolidates the metrics for specified repositories and creates CloudWatch dashboards to display them.
Actionable metrics for all repositories exist in one centralized dashboard, while details dashboards, one per repository, host the other metrics.
GitHub webhooks add another layer of complexity to the collected metrics.

## Prerequisites

### Install the AWS CDK

AWS Repository Status Monitor is an [AWS CDK](https://aws.amazon.com/cdk/) project. To run the launch script you must
have CDK installed:

```sh
$ npm install -g aws-cdk
```

### Set Up the AWS CLI

[Install the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)

To configure your AWS credentials for the AWS CLI:
```sh
$ aws configure
```

### Install Dependencies

AWS CDK uses virtualenv to keep required packages separated from your system Python. From the `RepositoryStatusMonitor`
directory, run the following commands:
```sh
$ python3 -m venv .env
$ source .env/bin/activate
$ pip install -r requirements.txt
```

## Configuration (Optional)
Before you can launch your dashboard, you'll need to set certain context variables, so the dashboard collects and displays
the data you desire. The `configuration` folder contains two config files for these context variables.

In `environment_config.json`, you can set the account and region into which you would like the app deployed. If the
values in this file are left empty, the account and region configured for the AWS CLI will be used.

In `context_variables.json`, you can specify all the context variables (described in detail in the Breakdown section below). Otherwise, all the
context variables contained in this file are set through the launch script. With the exception of GitHub and Docker
fields, all of those context variables can also be edited through the launch script. GitHub and Docker fields must be edited in this file.

## Creating the GitHub Personal Authentication Token
This token permits remote access to the GitHub API. It's necessary for automatically creating the GitHub webhooks that
send dynamic data and ensuring the GitHub API hourly request limit isn't breached. The GitHub token is another context
variable (`'github_token'`) but for added security it is stored in AWS Secrets Manager instead of `cdk.json` or `context_variables.json`.

* To create the token:
    * [See GitHub documentation on authorization](https://developer.github.com/v3/auth/#via-oauth-and-personal-access-tokens)
    * create your token by clicking on your icon in the top right corner -> Settings -> Developer settings -> Personal access tokens
    * make sure to give the token read permissions on the repository and user

## Creating and Deploying Your App

To launch your app, run the launch script:
```sh
$ ./launch.py
```

This will confirm that all the context variables are correct, create or update a secret in AWS Secrets Manager with the
GitHub token, synthesize the template, and deploy the stack. Using CDK commands (e.g. cdk synth, cdk deploy) to
accomplish this is not recommended because of the formatting requirements for context variables.

If the launch script has been run once, context variables will be saved, and the launch script can be run again
non-interactively. This command disables interactive mode:
```sh
$ ./launch.py --d
```

## Breakdown of Context Variables

* Lambda Timeout (`'lambda_timeout'`)
    * the timeout (in seconds) for the metric-handling Lambda function
    * if your Lambda regularly time out, you must increase this number
    * the max value for this variable is 30 seconds, since it must be lower than the SQS queue timeout
* Namespace (`'namespace'`)
    * the namespace for the metrics in CloudWatch
* User-Agent Header (`'user_agent_header'`)
    * the User-Agent header to be used for GitHub requests
* Dashboard Name Prefix (`'dashboard_name_prefix'`)
    * the prefix for all CloudWatch dashboards created by this app
* Owner (`'owner'`)
    * the GitHub owner of the repos whose metrics you would like to collect
    * if this variable is left empty, every repository must have its owner individually specified
        * e.g. `'owner': "", 'repo_names': 'owner/repo_name'`
    * if this variable is not empty, individually specified owners will take precedence
        * e.g. `'owner': "owner", 'repo_names': 'individual_owner/repo_name'`
* Repository Names (`'repo_names'`)
    * the list of repositories for which you would like to collect metrics
    * formatted as comma-separated string without spaces: `'repository-name-1,repository-name-2'`
    * owners for individual repositories are formatted: `'aws/aws-node-termination-handler'`
* Docker Opt-In (`'get_docker'`)
    * whether to collect metrics from Docker as well as GitHub
    * specify as `'y'` to collect metrics or `'n'` otherwise
* GitHub Fields
    * unpaginated (`github_fields_unpaginated`)
        * any metric that can be retrieved as a single value from some endpoint in the GitHub API
    * paginated (`github_fields_paginated`)
        * the fields that don't exist in the standard metrics returned by GitHub and whose data needs to be manually counted
* Docker Fields (`docker_fields`)
    * the Docker API fields to collect metrics from


Fields are formatted: `'Display Name': 'api_param'`. Example: `"GitHub Stars": "stargazers_count"`

Nested fields are formatted with `*`: `'Display Name: param1*param2*param3'`. Example: `"Issue Inactive Since": "issues?sort=created&direction=asc/0*updated_at"`

The base url for GitHub is `'https://api.github.com/repos/:owner/:repo` and for Docker is `'https://hub.docker.com/v2/repositories/amazon/'`.
Metrics from any other endpoint should be specified in the format: `'Display Name': 'url_ending/param1*param2'`.

Here is an example of the `configuration/context_variables.json` file:
```json
{
    "lambda_timeout": "300",
    "namespace": "RepositoryStatusMonitor",
    "user_agent_header": "RepositoryStatusMonitor",
    "dashboard_name_prefix": "MyMonitor",
    "owner": "haugenj",
    "repo_names": "haugenj/aws-repository-status-monitor",
    "get_docker": "n",
    "github_fields_unpaginated": {
        "GitHub Stars": "stargazers_count",
        "Forks": "forks_count",
        "Open Issues": "open_issues_count",
        "Watchers": "subscribers_count",
        "Latest GitHub Release": "releases/latest/tag_name",
        "Latest Release Asset Download Count": "releases/latest/assets",
        "GitHub Health Percentage": "community/profile/health_percentage",
        "Top Referrers Over 14 Days": "traffic/popular/referrers/",
        "Unique Clones Over 14 Days": "traffic/clones/uniques",
        "Unique Views Over 14 Days": "traffic/views/uniques",
        "Language Breakdown": "languages/",
        "Longest Inactive Issue": "issues?sort=created&direction=asc/0*title",
        "Issue Inactive Since": "issues?sort=created&direction=asc/0*updated_at",
        "Longest Inactive PR": "pulls?sort=updated/0*title",
        "PR Inactive Since": "pulls?sort=updated/0*updated_at"
    },
    "github_fields_paginated": {
        "Open Pull Requests": "pulls",
        "Contributors": "contributors"
    },
    "docker_fields": {
        "Docker Pull Count": "pull_count",
        "Latest Docker Release": "tags/results*0*name",
        "Image Size (in mb)": "tags/results*0*full_size",
        "CPU Architecture": "tags/results*0*images*0*architecture"
    }
}
```
## Running the Tests
To run the full suite of tests use the following steps:
```
# start the virtual env
$ source .env/bin/activate 

# install pytest
$ pip install pytest

# run the tests
$ pytest --github <github token> 
``` 

To run with code coverage:
```
$ pytest --github <github token> --cov
```

If you get errors about missing modules when running the tests and have pytest installed on your machine try following
the instructions [here](https://medium.com/@dirk.avery/pytest-modulenotfounderror-no-module-named-requests-a770e6926ac5)

## Example Dashboard

For two repositories with the default metrics collected, these pictures show examples of the main and details dashboard.
Note that when the dashboard is created the order of widgets on the page may not be to your liking, you can drag and drop
to rearrange the widget positions. Many of the widgets initially look like simple numbers, but they have multiple ways
of displaying their data as well that can be modified in the kebab menu of the widget.

### Main Dashboard:
![](README_resources/main_dashboard_example.png)

### Details Dashboards:
![](README_resources/details_dashboard_1.png)