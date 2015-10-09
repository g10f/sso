#!/usr/bin/env python
import httplib
import json
import argparse
from base64 import b64encode
from urllib import urlencode


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


def main():
    # command line arguments setup
    parser = argparse.ArgumentParser(description='DWBN IAM API Request')
    parser.add_argument('client_id')
    parser.add_argument('client_secret')
    parser.add_argument('-d', '--host', default='sso.dwbn.org')
    args = parser.parse_args()
    
    conn = httplib.HTTPSConnection(args.host)
    # authentication
    access_token = get_access_token_with_client_credentials(conn, args.client_id, args.client_secret)
    # API request
    data = get(conn, '/api/emails.txt', access_token)
    
    conn.close()
    print data


if __name__ == "__main__":
    main()
