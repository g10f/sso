import json
import os
from pyquery import PyQuery
from urllib import urlencode
from uritemplate import expand
from locust import HttpLocust, TaskSet, task
try:
    from urllib.parse import urlsplit
except ImportError:  # Python 2
    from urlparse import urlsplit


OAUTH2_CLIENT = {
    'host': 'https://sso-dev.dwbn.org',
    # 'host': 'http://localhost:8000',
    'grant_type': 'authorization_code',
    'scope': 'openid profile email',
    'response_type': 'code',
    'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
    'client_id': os.environ['CLIENT_ID'],
    'client_secret': os.environ['CLIENT_SECRET'],
    'username': os.environ['USERNAME'],
    'password': os.environ['PASSWORD'],
}


class UserBehavior(TaskSet):    
    @property
    def authentication_uri(self):
        query = {
            'scope': OAUTH2_CLIENT['scope'],
            'client_id': OAUTH2_CLIENT['client_id'],
            'state': 'locust_test',
            'response_type': OAUTH2_CLIENT['response_type'],
            'redirect_uri': OAUTH2_CLIENT['redirect_uri']
        }
        return "%s?%s" % (self.openid_configuration['authorization_endpoint'], urlencode(query))
    
    def on_start(self):
        """ on_start is called when a Locust start before any task is scheduled """
        response = self.client.get('/.well-known/openid-configuration')
        self.openid_configuration = json.loads(response.content)

    @task
    def login(self):
        # SSO login for installed apps to get an auth code
        response = self.client.get(self.authentication_uri)
        pq = PyQuery(response.content)
        headers = {"referer": response.request.url}
        data = {
            "username": OAUTH2_CLIENT['username'], 
            "password": OAUTH2_CLIENT['password'],
            "csrfmiddlewaretoken": pq("input[name='csrfmiddlewaretoken']").val(), 
            "this_is_the_login_form": "1",
            "login_form_key": "login_form",
            "next": pq("input[name='next']").val()
        }
        response = self.client.post(response.request.path_url, data=data, headers=headers)
        pq = PyQuery(response.content)
        
        # user logout, because we have now a auth code to authenticate 
        self.client.get(self.openid_configuration['end_session_endpoint'])
        
        # use the auth code to get a token
        data = {
            'grant_type': OAUTH2_CLIENT['grant_type'],
            'client_id': OAUTH2_CLIENT['client_id'],
            'client_secret': OAUTH2_CLIENT['client_secret'],
            'code': pq("#code").val(),
            'redirect_uri': OAUTH2_CLIENT['redirect_uri']
        }
        headers = {'content-type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}
        response = self.client.post(self.openid_configuration['token_endpoint'], data=data, headers=headers)
        content = json.loads(response.content)
        
        # get userinfo
        headers = {
            'accept': 'application/json',
            'authorization': '%s %s' % (content['token_type'], content['access_token'])            
        }
        self.client.get(self.openid_configuration['userinfo_endpoint'], headers=headers)
        
    #@task
    def index(self):
        self.client.get("/")


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait = 1000
    max_wait = 2000
    host = OAUTH2_CLIENT['host']
