from unittest.mock import patch

from lambda_dir import http_handler as hh


@patch('lambda_dir.http_handler.http.request')
def test_request_handler_good_github_request(mock_get):
    mock_get.return_value.status = 200
    mock_get.return_value.data = "{'data': 'd'}".encode()
    success, data, res_headers = hh.request_handler(url='test-url', headers={})
    assert success


@patch('lambda_dir.http_handler.http.request')
def test_request_handler_bad_github_request_with_message(mock_get, capfd):
    mock_get.return_value.status = 403
    mock_get.return_value.data = "{'message': 'Testing bad request'}".encode()
    success, data, res_headers = hh.request_handler(url='test-url', headers={})
    assert not success
    assert 'Testing bad request' in capfd.readouterr()[0]


@patch('lambda_dir.http_handler.http.request')
def test_request_handler_bad_github_request_no_message(mock_get, capfd):
    mock_get.return_value.status = 403
    mock_get.return_value.data = 'Request not put through.'.encode()
    success, data, res_headers = hh.request_handler(url='test-url', headers={})
    assert success
    assert 'Request failed:  Request not put through.' in capfd.readouterr()[0]


@patch('lambda_dir.http_handler.request_handler')
def test_handle_pagination_correct(mock_get):
    data = ['first']
    res_headers = {'Link': 'lastlink?page=2; rel=\"last\"'}
    mock_get.return_value = True, ['second'], {}
    success, data = hh.handle_pagination(url='test-url', data=data, request_headers={}, response_headers=res_headers,
                                         http_fields={})
    assert success
    assert data == ['first', 'second']


@patch('lambda_dir.http_handler.request_handler')
def test_handle_pagination_no_more_pages(mock_get):
    data = ['first']
    res_headers = {'Link': 'lastlink?page=2; rel=\"next\"'}
    mock_get.return_value = True, ['second'], {}
    success, data = hh.handle_pagination(url='test-url', data=data, request_headers={}, response_headers=res_headers,
                                         http_fields={})
    assert not success
    assert 'first' in data
    assert 'second' not in data
