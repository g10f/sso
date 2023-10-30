#!/usr/bin/env python
import argparse
import logging
import sys

from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from uritemplate import expand

logging.basicConfig(stream=sys.stdout, level='INFO', format="%(levelname)s %(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='IAM API Request')
    parser.add_argument('client_id')
    parser.add_argument('client_secret')
    parser.add_argument('-b', '--base_uri', help='The base_uri of the API ..', default='http://localhost:8000')
    parser.add_argument('-r', '--resource',
                        help='the resource name from the API EntryPoint (see https://<host>/api/ )',
                        default='user_app_role')
    parser.add_argument('--disable_ssl_certificate_validation', dest='disable_ssl_certificate_validation',
                        action='store_true', default=True)

    # uri template parameters
    parser.add_argument('--user_id', default='a8992f0348634f76b0dac2de4e4c83ee', help='uuid of the user for the user resource')
    parser.add_argument('--app_id', default='bc0ee635a536491eb8e7fbe5749e8111', help='uuid of the application')
    parser.add_argument('--role', default='Staff', help='role')

    # get a dictionary with the command line arguments
    args = vars(parser.parse_args())
    base_uri = args.pop('base_uri')
    resource = args.pop('resource')
    client_id = args.pop('client_id')
    client_secret = args.pop('client_secret')
    verify = args.pop('disable_ssl_certificate_validation')

    scope = 'openid role'
    session = OAuth2Session(client=BackendApplicationClient(client_id=client_id, client_secret=client_secret,scope=scope), scope=scope)
    session.verify = verify
    openid_configuration = session.get(base_uri + "/.well-known/openid-configuration").json()
    session.fetch_token(token_url=openid_configuration['token_endpoint'], client_secret=client_secret)
    api_entry_point = session.get(base_uri + '/api/').json()
    url = expand(api_entry_point[resource], args)

    try:
        data = session.put(url)
        print(data.json())
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
