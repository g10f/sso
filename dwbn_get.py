#!/usr/bin/env python
import httplib
import json
import argparse
from base64 import b64encode
from urllib import urlencode
from uritemplate import expand
try:
    from urllib.parse import urlsplit
except ImportError:  # Python 2
    from urlparse import urlsplit


def get(conn, uri, access_token=None):
    """
    HTTP GET request with an optional authorization header with the access_token 
    """
    if access_token:
        headers = {'authorization': '%s %s' % (access_token['token_type'], access_token['access_token'])}
    else:
        headers = {}
    conn.request('GET', uri, headers=headers)
    response = conn.getresponse()
    return response.read()


def get_json(conn, uri, access_token=None):
    return json.loads(get(conn, uri, access_token))


def get_access_token_with_client_credentials(conn, client_id, client_secret):
    """
    get the token endpoint from the well-known uri and 
    then authenticate with grant_type client_credentials
    """
    openid_configuration = get_json(conn, '/.well-known/openid-configuration')
    token_endpoint = openid_configuration['token_endpoint']
    
    body = urlencode({'grant_type': 'client_credentials'})
    auth = b"%s:%s" % (client_id, client_secret)
    headers = {'Content-Type': 'application/x-www-form-urlencoded', 'authorization': '%s %s' % ('Basic', b64encode(auth).decode("ascii"))}
    conn.request('POST', token_endpoint, headers=headers, body=body)
    response = conn.getresponse()
    json_response = json.loads(response.read())
    if 'error' in json_response:
        raise Exception('authorization', json_response)
    else:
        return json_response


def get_url(conn, resource, args):
    """
    get information about the resource from  API EntryPoint 
    expand the uri template and return the path with the query string.
    """
    api_entry_point = get_json(conn, '/api/')
    url = expand(api_entry_point[resource], args)
    (scheme, netloc, path, query, fragment) = urlsplit(url)
    return path + "?" + query


def main():
    parser = argparse.ArgumentParser(description='DWBN IAM API Request')
    parser.add_argument('client_id')
    parser.add_argument('client_secret')
    parser.add_argument('-o', '--host', help='The host name where the API ..', default='sso.dwbn.org')
    parser.add_argument('-r', '--resource', help='the resource name from the API EntryPoint (see https://<host>/api/ )', default='organisations')
    
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
    host = args.pop('host')
    resource = args.pop('resource')
    client_id = args.pop('client_id')
    client_secret = args.pop('client_secret')    
    conn = httplib.HTTPSConnection(host)
    
    access_token = get_access_token_with_client_credentials(conn, client_id, client_secret)
    url = get_url(conn, resource, args)
   
    data = get_json(conn, url, access_token)
    print json.dumps(data)
    while 'next_page' in data:
        url = data['next_page']
        data = get_json(conn, url, access_token)
        print json.dumps(data)

    conn.close()


if __name__ == "__main__":
    main()
