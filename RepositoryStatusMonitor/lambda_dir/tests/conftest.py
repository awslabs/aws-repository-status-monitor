import os
import sys

import pytest


def pytest_sessionstart(session):
    test_path = sys.path[0]
    lambda_path = test_path.rsplit('/', 1)[0]
    project_path = lambda_path.rsplit('/', 1)[0]
    if lambda_path not in sys.path:
        sys.path.insert(0, lambda_path)
    if project_path not in sys.path:
        sys.path.insert(0, project_path)


@pytest.fixture(scope='session', autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_REGION'] = 'us-west-2'
