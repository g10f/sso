#!/usr/bin/env python
import httplib2
import json
import sys
import os
import argparse
from datetime import datetime, timedelta
from base64 import b64encode
from urllib import urlencode
from uritemplate import expand

import logging

logging.basicConfig(stream=sys.stdout, level='DEBUG', format="%(levelname)s %(asctime)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read_from_file(filename, silent=True, format='json'):
    path = os.path.join(BASE_DIR, 'data', filename)
    try:
        with open(path, 'r') as f:
            if format == 'json':
                return json.load(f)
            else:
                return f.read()
    except:
        if silent:
            pass
        else:
            raise e


def put_to_file(filename, data, format='json'):
    path = os.path.join(BASE_DIR, 'data', filename)
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))        
    with open(path, 'w') as f:
        if format == 'json':
            json.dump(data, f, indent=4)
        else:
            f.write(data)


class TokenCache(object):
    def __init__(self, base_uri, client_id, client_secret):
        self.base_uri = base_uri
        self.client_id = client_id
        self.client_secret = client_secret
    
        self.cache = read_from_file("token_cache.json", format="json")
        if self.cache is None:
            self.refresh()

    @property
    def auth_header(self):
        return {'authorization': '%s %s' % (self.cache.get('token_type', ''), self.cache.get('access_token', ''))}
    
    
    def refresh(self):
        """
        get the token endpoint from the well-known uri and 
        then authenticate with grant_type client_credentials
        """
        http = httplib2.Http(cache=".cache")
        openid_configuration = _get(http, self.base_uri + '/.well-known/openid-configuration')
        token_endpoint = openid_configuration['token_endpoint']
        
        body = urlencode({'grant_type': 'client_credentials'})
        auth = b"%s:%s" % (self.client_id, self.client_secret)
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'authorization': '%s %s' % ('Basic', b64encode(auth).decode("ascii"))}
        json_response = _post(http, token_endpoint, headers=headers, body=body)
        if 'error' in json_response:
            logger.error(content)
            raise Exception('authorization', json_response)
        else:
            self.cache = json_response
            put_to_file("token_cache.json", self.cache, format="json")
    
def _post(http, uri, headers=None, body=None):
    (response, content) = http.request(uri, 'POST', headers=headers, body=body)
    return json.loads(content)
    
def _get(http, uri, headers=None):
    """
    HTTP GET request with an optional authorization header with the access_token 
    """
    (response, content) = http.request(uri, 'GET', headers=headers)
    return json.loads(content)


def get(uri, token_cache=None):
    if token_cache:
        http = httplib2.Http()    
        headers = token_cache.auth_header
        data =  _get(http, uri, headers)
        if ('error' in data) and (data['code'] == 401):
            # try with fresh access token
            token_cache.refresh()
            headers = token_cache.auth_header
            data = _get(http, uri, headers)
    else:
        # use cache when there is no token
        http = httplib2.Http(cache=".cache")
        data = _get(http, uri)

    return data


def now():
    dt = datetime.utcnow()
    r = dt.isoformat()
    if dt.microsecond:
        r = r[:23] + r[26:]
    r += 'Z'
    return r


def update_item(item, token_cache, resource):
    def is_outdated(fname):
        date_fmt = '%Y-%m-%dT%H:%M:%S.%fZ'
        try:
            with open(fname, 'r') as f:
                center_data = json.load(f)
                
            last_modified_item = datetime.strptime(item['last_modified'], date_fmt)
            if (center_data and 'last_modified' in center_data):
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
            data = get(url, token_cache)
            json.dump(data, f, indent=4)


def load_collection(base_uri, resource, args, token_cache):
    def write_tik():
        sys.stdout.write('.')
        sys.stdout.flush()
    
    api_entry_point = get(base_uri + '/api/')
    modified_since_data = read_from_file("modified_since.json")
    key = expand(api_entry_point[resource], args)
    if modified_since_data is not None:
        modified_since = modified_since_data.get(key, None)
    else:
        modified_since = None

    # expand the uri template with modified_since from last request
    params = args.copy()    
    params.update({'modified_since': modified_since })
    url = expand(api_entry_point[resource], params)
    
    # update modified_since
    modified_since = now()
    
    # updated items
    while url:
        write_tik()
        
        data = get(url, token_cache)
        if 'error' in data:
            raise Exception(data)
        
        for item in data['member']:
            write_tik()
            update_item(item, token_cache, resource)                
                                          
        url = data['next_page']  if 'next_page' in data else None

    print ''
    
    # update modified_since
    modified_since_data = read_from_file("modified_since.json")
    if modified_since_data is None:
        modified_since_data = {}
    modified_since_data[key] = modified_since
    put_to_file("modified_since.json", modified_since_data)


def main():
    parser = argparse.ArgumentParser(description='DWBN IAM API Request')
    parser.add_argument('client_id')
    parser.add_argument('client_secret')
    parser.add_argument('-b', '--base_uri', help='The base_uri of the API ..', default='https://sso.dwbn.org')
    parser.add_argument('-r', '--resource', help='the resource name of the collection from the API EntryPoint (see https://<host>/api/ )', default='organisations')
    
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
    
    token_cache = TokenCache(base_uri, client_id, client_secret)

    load_collection(base_uri, resource, args, token_cache)


if __name__ == "__main__":
    main()
