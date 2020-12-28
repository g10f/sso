#!/usr/bin/env python
import argparse
import logging

import sys
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from uritemplate import expand

logging.basicConfig(stream=sys.stdout, level='INFO', format="%(levelname)s %(asctime)s: %(message)s")
logger = logging.getLogger(__name__)


def print_app_roles(session, data, app_uuid):
    for member in data['member']:
        member_details = session.get(member['@id']).json()
        if app_uuid in member_details['apps']:
            print(member_details['name'], member_details['apps'][app_uuid]['roles'])


def main():
    parser = argparse.ArgumentParser(description='IAM API Request')
    parser.add_argument('client_id')
    parser.add_argument('client_secret')
    parser.add_argument('-b', '--base_uri', help='The base_uri of the API ..', default='https://sso.g10f.de')
    parser.add_argument('-r', '--resource',
                        help='the resource name from the API EntryPoint (see https://<host>/api/ )',
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
    parser.add_argument('--app_id', help='uuid of the application')

    # get a dictionary with the command line arguments
    args = vars(parser.parse_args())
    base_uri = args.pop('base_uri')
    resource = args.pop('resource')
    client_id = args.pop('client_id')
    client_secret = args.pop('client_secret')
    verify = args.pop('disable_ssl_certificate_validation')

    session = OAuth2Session(client=BackendApplicationClient(client_id=client_id, client_secret=client_secret,
                                                            scope='openid profile email users role tt'))
    session.verify = verify
    openid_configuration = session.get(base_uri + "/.well-known/openid-configuration").json()
    session.fetch_token(token_url=openid_configuration['token_endpoint'], client_secret=client_secret)
    api_entry_point = session.get(base_uri + '/api/').json()
    url = expand(api_entry_point[resource], args)

    while True:
        data = session.get(url).json()
        print_app_roles(session, data, 'e0db912c871e4d1784d2b60aada2e234')

        if 'next_page' in data:
            url = data['next_page']
        else:
            break


if __name__ == "__main__":
    main()
