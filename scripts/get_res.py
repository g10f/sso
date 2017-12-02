#!/usr/bin/env python
import argparse
import json
import logging
import sys
from base64 import b64encode
from urllib.parse import urlencode

import requests
from uritemplate import expand

logging.basicConfig(stream=sys.stdout, level='DEBUG', format="%(levelname)s %(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


def get_json(session, uri, access_token=None):
    if access_token:
        headers = {'authorization': '%s %s' % (access_token['token_type'], access_token['access_token'])}
    else:
        headers = {}
    return session.get(uri, headers=headers).json()


def get_access_token_with_client_credentials(session, base_uri, client_id, client_secret):
    """
    get the token endpoint from the well-known uri and 
    then authenticate with grant_type client_credentials
    """
    openid_configuration = get_json(session, base_uri + '/.well-known/openid-configuration')
    token_endpoint = openid_configuration['token_endpoint']

    body = urlencode({'grant_type': 'client_credentials'})
    auth = b"%s:%s" % (client_id.encode(), client_secret.encode())
    # e2U5MWM4YWUxNThmYzQ0NTViYWE1Y2EzYWVkOTdlMjFjfTp7Tm8wcTBnVHJrUGVoMUF4Uk5aZEF5OURNZzVZa2JHfQ==
    headers = {'Content-Type': 'application/x-www-form-urlencoded',
               'authorization': '%s %s' % ('Basic', b64encode(auth).decode("ascii"))}
    json_response = session.post(token_endpoint, headers=headers, data=body).json()
    if 'error' in json_response:
        logger.error(json_response)
        raise Exception('authorization', json_response)
    else:
        return json_response


def get_url(session, base_uri, resource, args):
    """
    get information about the resource from  API EntryPoint 
    expand the uri template and return the path with the query string.
    """
    api_entry_point = get_json(session, base_uri + '/api/')
    url = expand(api_entry_point[resource], args)
    return url


def main():
    parser = argparse.ArgumentParser(description='IAM API Request')
    parser.add_argument('client_id')
    parser.add_argument('client_secret')
    parser.add_argument('-b', '--base_uri', help='The base_uri of the API ..', default='https://sso.g10f.de')
    parser.add_argument('-r', '--resource', help='the resource name from the API EntryPoint (see https://<host>/api/ )',
                        default='organisations')
    parser.add_argument('--disable_ssl_certificate_validation', dest='disable_ssl_certificate_validation',
                        action='store_true', default=True)

    # uri template parameters
    parser.add_argument('--q', help='text search parameter for name, email, ..')
    parser.add_argument('--per_page', help='items per page if the resource is a collection')
    parser.add_argument('--country', help='ISO alpha-2 country code filter for collections ')
    parser.add_argument('--latlng', help='latitude,longitude of a point from where the distance is calculated')
    parser.add_argument('--dlt', help='distance less then filter in km ')
    parser.add_argument('--modified_since', help='date time filter')
    parser.add_argument('--user_id', help='uuid of the user for the user resource')
    parser.add_argument('--org_id', help='uuid of the organisation for the organisation resource')

    # get a dictionary with the command line arguments
    args = vars(parser.parse_args())
    base_uri = args.pop('base_uri')
    resource = args.pop('resource')
    client_id = args.pop('client_id')
    client_secret = args.pop('client_secret')
    verify = args.pop('disable_ssl_certificate_validation')

    session = requests.Session()
    session.verify = verify
    access_token = get_access_token_with_client_credentials(session, base_uri, client_id, client_secret)

    url = get_url(session, base_uri, resource, args)

    data = get_json(session, url, access_token)
    print(json.dumps(data))

    while 'next_page' in data:
        url = data['next_page']
        data = get_json(session, url, access_token)
        print(json.dumps(data))


if __name__ == "__main__":
    main()
