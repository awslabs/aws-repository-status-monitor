import json
import re

import urllib3

http = urllib3.PoolManager()


def request_handler(url: str, method='GET', headers=None, http_fields=None, post_body=None) -> tuple:
    """Performs an HTTP request to the specified URL and gracefully handles a failed request

    :param url: the url to query
    :type url: str
    :param method: the HTTP method to perform (default is "GET")
    :type method: Optional[str]
    :param headers: the HTTP headers to send with the request
    :type headers: Optional[dict]
    :param http_fields: the HTTP fields to send with the request
    :type http_fields: Optional[dict]
    :param post_body: the data to post if the method is 'POST'
    :type post_body: Optional[str]
    :returns: the success of the request, the data returned by the request, the headers of the response
    :rtype: tuple
    """
    response = http.request(method, url, headers=headers, fields=http_fields, body=post_body)
    decoded_data = response.data.decode('utf-8')
    try:
        data_dict = json.loads(decoded_data)
    except json.decoder.JSONDecodeError:
        data_dict = {'message': decoded_data}

    if response.status < 200 or response.status >= 300:
        print('Request for ' + url + "failed. Response data:")
        print(decoded_data)
        return False, data_dict, response.headers

    return True, data_dict, response.headers


def handle_pagination(url: str, data: list, response_headers: dict, http_fields: dict, request_headers=None) -> tuple:
    """Handles retrieving the remaining data for a request that is paginated

    :param url: the url to query
    :type url: str
    :param data: the data from the first request
    :type data: list
    :param response_headers: the HTTP response headers containing the pagination links
    :type response_headers: dict
    :param http_fields: the HTTP fields to send with the request
    :type http_fields: dict
    :param request_headers: the HTTP headers to send with the request
    :type request_headers: Optional[dict]
    :returns: the success of the request, the complete data retrieved by all the paginated requests
    :rtype: tuple
    """
    if 'Link' in response_headers.keys():
        last_link = None
        for link in response_headers['Link'].split(','):
            if 'rel=\"last\"' in link:
                last_link = link.split(';')[0]

        if last_link is not None:
            match = re.search(r'[?&]page=([^&]+)', last_link)
            if match:
                total_pages = int(match.groups()[0])
                for i in range(2, total_pages + 1):
                    http_fields['page'] = i
                    next_success, next_data, next_headers = request_handler(url,
                                                                            headers=request_headers,
                                                                            http_fields=http_fields)
                    if next_success:
                        data.extend(next_data)

            return True, data

    return False, data
