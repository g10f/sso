#!/usr/bin/env python
import argparse
import json
import logging
import os
import sys
from base64 import b64encode

import requests
from datetime import datetime
from uritemplate import expand

logging.basicConfig(stream=sys.stdout, level='WARNING', format="%(levelname)s %(asctime)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def now():
    """
    UTC datetime string with format yyy-mm-ddThh:mm.sssZ
    """
    dt = datetime.utcnow()
    r = dt.isoformat()
    if dt.microsecond:
        r = r[:23] + r[26:]
    r += 'Z'
    return r


class FileCache(object):
    """
    Uses a local file as a store for responses of some more or less static resources like
    api entry point, .well-known/openid-configuration and 
    the access_token response 
    """

    def __init__(self, filename):
        self.data = {}
        self.path = os.path.join(BASE_DIR, 'data', filename)
        try:
            with open(self.path, 'r') as f:
                self.data = json.load(f)
        except Exception as e:
            pass

    def get(self, key, default=None):
        try:
            return self.data.get(key, default)
        except Exception as e:
            pass

    def set(self, key, value):
        self.data[key] = value
        if not os.path.exists(os.path.dirname(self.path)):
            os.makedirs(os.path.dirname(self.path))
        with open(self.path, 'w') as f:
            json.dump(self.data, f, indent=4)


class ApiClient(object):
    def __init__(self, base_uri, client_id, client_secret):
        self.base_uri = base_uri
        self.client_id = client_id
        self.client_secret = client_secret
        self.cache = FileCache("api_cache.json")
        self.session = requests.Session()

    @property
    def auth_header(self):
        """
        authorization header
        """
        if self.base_uri not in self.cache.get('token_endpoint', {}):
            self.get_token()
        token_endpoint = self.cache.get('token_endpoint')[self.base_uri]

        return {
            'authorization': '%s %s' % (token_endpoint.get('token_type', ''), token_endpoint.get('access_token', ''))}

    def get_token(self):
        """
        get the token endpoint from the well-known uri and 
        then authenticate with grant_type client_credentials
        """
        openid_configuration = self._get_cached(self.base_uri + '/.well-known/openid-configuration')
        token_endpoint = openid_configuration['token_endpoint']

        body = {'grant_type': 'client_credentials'}
        auth = b"%s:%s" % (self.client_id, self.client_secret)
        headers = {'Content-Type': 'application/x-www-form-urlencoded',
                   'authorization': '%s %s' % ('Basic', b64encode(auth).decode("ascii"))}
        json_response = self.session.post(token_endpoint, headers=headers, data=body).json()
        if 'error' in json_response:
            logger.error(json_response)
            raise Exception('authorization', json_response)
        else:
            self.cache.set('token_endpoint', {self.base_uri: json_response})

    def get(self, uri):
        """
        make authorized request
        """
        headers = self.auth_header
        data = self.session.get(uri, headers=headers).json()
        if ('error' in data) and (data['code'] == 401):
            # try with fresh access token
            self.get_token()
            headers = self.auth_header
            data = self.session.get(uri, headers=headers).json()
        return data

    def _get_cached(self, uri):
        # performance optimisation helper
        cached_uris = self.cache.get('cached_uris', {})
        if uri not in cached_uris:
            json_response = self.session.get(uri).json()
            cached_uris[uri] = json_response
            self.cache.set('cached_uris', cached_uris)
        return self.cache.get('cached_uris')[uri]

    def load_collection(self, resource, args):
        """
        load the collection resource with modified since from the last request and 
        iterate trough all items.
        If the item is outdated, make a request for the item resource and update the 
        item stored in the file system
        """

        def write_dot():
            sys.stdout.write('.')
            sys.stdout.flush()

        api_entry_point = self._get_cached(self.base_uri + '/api/')
        key = expand(api_entry_point[resource], args)
        modified_since = self.cache.get('modified_since', {}).get(key, None)

        # expand the uri template with modified_since from last request
        params = args.copy()
        params.update({'modified_since': modified_since})
        url = expand(api_entry_point[resource], params)

        # update modified_since
        modified_since = now()

        # updated items
        while url:
            write_dot()

            data = self.get(url)
            if 'error' in data:
                raise Exception(data)

            for item in data['member']:
                write_dot()
                self.update_item(item, resource)

            url = data['next_page'] if 'next_page' in data else None

        print('')

        # update modified_since
        modified_since_cache = self.cache.get('modified_since', {})
        modified_since_cache[key] = modified_since
        self.cache.set('modified_since', modified_since_cache)

    def update_item(self, item, resource):
        """
        get new data for the item, if the filesystem data are outdated
        """

        def is_outdated(fname):
            date_fmt = '%Y-%m-%dT%H:%M:%S.%fZ'
            try:
                with open(fname, 'r') as f:
                    center_data = json.load(f)

                last_modified_item = datetime.strptime(item['last_modified'], date_fmt)
                if center_data and 'last_modified' in center_data:
                    last_modified_center_data = datetime.strptime(center_data['last_modified'], date_fmt)
                    return last_modified_item > last_modified_center_data
                return True
            except:
                return True

        path = os.path.join(BASE_DIR, 'data', resource, "%s.json" % item['id'])
        if is_outdated(path):
            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            with open(path, 'w') as f:
                url = item['@id']
                data = self.get(url)
                json.dump(data, f, indent=4)


def main():
    parser = argparse.ArgumentParser(description='IAM API Request')
    parser.add_argument('client_id')
    parser.add_argument('client_secret')
    parser.add_argument('-b', '--base_uri', help='The base_uri of the API ..', default='https://sso.g10f.de')
    parser.add_argument('-r', '--resource',
                        help='the resource name of the collection from the API EntryPoint (see https://<host>/api/ )',
                        default='organisations')

    # uri template parameters
    parser.add_argument('--q', help='text search parameter for name, email, ..')
    parser.add_argument('--per_page', help='items per page if the resource is a collection')
    parser.add_argument('--country', help='ISO alpha-2 country code filter for collections ')
    parser.add_argument('--region_id', help='region id filter for collections ')
    parser.add_argument('--latlng', help='latitude,longitude of a point from where the distance is calculated')
    parser.add_argument('--dlt', help='distance less then filter in km ')
    parser.add_argument('--modified_since', help='date time filter')

    # get a dictionary with the command line arguments
    args = vars(parser.parse_args())
    base_uri = args.pop('base_uri')
    resource = args.pop('resource')
    client_id = args.pop('client_id')
    client_secret = args.pop('client_secret')

    client = ApiClient(base_uri, client_id, client_secret)
    try:
        client.load_collection(resource, args)
    except Exception as e:
        logger.exception(e)


if __name__ == "__main__":
    main()
