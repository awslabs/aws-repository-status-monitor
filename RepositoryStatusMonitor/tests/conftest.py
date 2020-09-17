import sys


def pytest_sessionstart(session):
    lambda_path = sys.path[0] + '/lambda_dir'
    if lambda_path not in sys.path:
        sys.path.insert(0, lambda_path)


def pytest_addoption(parser):
    parser.addoption('--github', action='store', default='1234')


def pytest_generate_tests(metafunc):
    # This is called for every test. Only get/set command line arguments
    # if the argument is specified in the list of test "fixturenames".
    option_value = metafunc.config.option.github
    if 'github' in metafunc.fixturenames and option_value is not None:
        metafunc.parametrize('github', [option_value])
