import os
import re
from base64 import b64encode
from urllib.parse import urlencode, urlsplit, parse_qs

from locust import HttpLocust, TaskSet, task
from pyquery import PyQuery

pattern = re.compile("^{(?P<env_var>.*)}$")

test_data = {
    "g10f_user": {
        "username": "{G10F_USER_NAME}",
        "password": "{G10F_USER_PASSWORD}",
    },
    "g10f_oidc_web_client": {
        "client_id": "{G10F_OIDC_WEB_CLIENT_ID}",
        "client_secret": "{G10F_OIDC_WEB_CLIENT_SECRET}",
        "redirect_uri": "http://localhost:8001/oauth2/login/",
        "scope": "openid profile email",
        'grant_type': 'authorization_code',
        'response_type': 'code',
    },
    "idp": {
        "oidc": {
            "verify_tls": False,
            "iss": "https://sso.elsapro.com",
        }
    },
    "proxies": {
        "http": "{http_proxy}",
        "https": "{https_proxy}"
    }
}


def update_values_from_environment(data):
    # iterate thru dict
    for k, v in data.items():
        if isinstance(v, dict):
            # if value is a dict iterate
            update_values_from_environment(v)
        elif isinstance(v, str):
            # find {NAME} patterns
            m = pattern.match(v)
            if m:
                # update configuration
                env_var = m.group('env_var')
                if os.environ.get(env_var) is not None:
                    data[k] = os.environ.get(env_var)


update_values_from_environment(test_data)


class UserBehavior(TaskSet):
    def __init__(self, parent):
        super().__init__(parent)
        self.openid_configuration = {}
        self.proxies = {}  # test_data['proxies']

    def get_authentication_uri(self, client):
        query = {
            'scope': client['scope'],
            'client_id': client['client_id'],
            'state': 'locust_test',
            'response_type': client['response_type'],
            'redirect_uri': client['redirect_uri']
        }
        return "%s?%s" % (self.openid_configuration['authorization_endpoint'], urlencode(query))

    def on_start(self):
        """ on_start is called when a Locust start before any task is scheduled """
        response = self.client.get('/.well-known/openid-configuration', proxies=self.proxies)
        self.openid_configuration = response.json()

    @task
    def login(self):
        # SSO login for installed apps to get an auth code
        user = test_data['g10f_user']
        client = test_data['g10f_oidc_web_client']
        headers = {"referer": client['redirect_uri']}
        response = self.client.get(self.get_authentication_uri(client), headers=headers, proxies=self.proxies,
                                   name=urlsplit(self.openid_configuration['authorization_endpoint']).path)
        pq = PyQuery(response.content)
        data = {
            "username": user['username'],
            "password": user['password'],
            "csrfmiddlewaretoken": pq("input[name='csrfmiddlewaretoken']").val(),
            "login_form_key": "login_form",
            "next": pq("input[name='next']").val()
        }
        path_url = response.request.path_url
        headers={"referer": response.request.url}
        response = self.client.post(path_url, data=data, headers=headers,
                                    proxies=self.proxies,
                                    allow_redirects=False,
                                    name=urlsplit(path_url).path)
        response = self.client.get(response.next.url, headers=headers, proxies=self.proxies,
                                   allow_redirects=False,
                                   name=urlsplit(response.next.url).path)
        query = parse_qs(urlsplit(response.next.url).query)

        # user logout, because we have now a auth code to authenticate
        self.client.get(self.openid_configuration['end_session_endpoint'], proxies=self.proxies)

        headers = {'content-type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}
        client_id = client['client_id']
        client_secret = client['client_secret']
        data = {
            'grant_type': 'authorization_code',
            'code': query['code'][0],
            'redirect_uri': client['redirect_uri']
        }
        # if code_verifier:
        #    data['code_verifier'] = code_verifier
        if client_secret:
            auth = b"%s:%s" % (client_id.encode(), client_secret.encode())
            headers['authorization'] = '%s %s' % ('Basic', b64encode(auth).decode("ascii"))

        response = self.client.post(self.openid_configuration['token_endpoint'], data=data, headers=headers,
                                    proxies=self.proxies)

        content = response.json()
        headers = {
            'accept': 'application/json',
            'authorization': '%s %s' % (content['token_type'], content['access_token'])
        }
        self.client.get(self.openid_configuration['userinfo_endpoint'], headers=headers, proxies=self.proxies)


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait = 1000
    max_wait = 2000
    host = "{0}://{1}".format(*urlsplit(test_data['idp']['oidc']['iss']))
