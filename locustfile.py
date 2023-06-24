import base64
import hashlib
import json
import os
from random import choice
from urllib.parse import urlencode, parse_qs
from urllib.parse import urlsplit

from locust import task, FastHttpUser, between, run_single_user
from pyquery import PyQuery


def get_random_string(length=12,
                      allowed_chars='abcdefghijklmnopqrstuvwxyz'
                                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    """
    Return a securely generated random string.

    The default length of 12 with the a-z, A-Z, 0-9 character set returns
    a 71-bit value. log_2((26+26+10)^12) =~ 71 bits
    """
    return ''.join(choice(allowed_chars) for _ in range(length))


def get_pkce():
    code_verifier = get_random_string(128)
    digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=')
    code_challenge_method = 'S256'
    return code_verifier, code_challenge, code_challenge_method


class WebsiteUser(FastHttpUser):
    wait_time = between(1, 5)
    oidc_config = {}
    host = os.getenv('HOST', '')

    def get_authentication_uri(self, **kwargs):
        query = {
            'scope': os.getenv('IDP_SCOPE', 'openid'),
            'client_id': os.getenv('IDP_CLIENT_ID', 'ec1e39cb-e3e7-46c7-87b7-70ace4165d13'),
            'state': get_random_string(),
            'response_type': 'code',
            'redirect_uri': os.getenv('IDP_REDIRECT_URI', 'http://localhost:8000/oauth2/login/'),
            'nonce': get_random_string(),
        }
        return "%s?%s" % (urlsplit(self.oidc_config['authorization_endpoint']).path, urlencode({**query, **kwargs}))

    def on_start(self):
        oidc_config_url = f"{os.getenv('IDP_BASE_URL', '')}/.well-known/openid-configuration"
        with self.rest("GET", oidc_config_url) as resp:
            if resp.js is None:
                pass  # no need to do anything, already marked as failed
            else:
                self.oidc_config = resp.js

    @task
    def login(self):
        config = self.oidc_config
        code_verifier, code_challenge, code_challenge_method = get_pkce()
        authentication_uri = self.get_authentication_uri(code_challenge=code_challenge,
                                                         code_challenge_method=code_challenge_method)
        response = self.client.get(authentication_uri, name=urlsplit(config['authorization_endpoint']).path)
        if response.status_code != 200:
            raise Exception("Failed to get login page")
        pq = PyQuery(response.text)
        data = {
            "username": os.getenv('IDP_USER', 'LoadtestUser'),
            "password": os.getenv('IDP_PASSWORD'),
            "csrfmiddlewaretoken": pq("input[name='csrfmiddlewaretoken']").val(),
            # "login_form_key": "login_form",
        }
        # sso has one internal redirect
        response = self.client.post(f"{urlsplit(response.url).path}?{urlsplit(response.url).query}", data=data, headers={"referer": response.url},
                                    allow_redirects=False,
                                    name=urlsplit(response.url).path)

        if 'location' not in response.headers:
            pq = PyQuery(response.text)
            error_text = pq('div[class="alert alert-danger"]').text()
            raise Exception(f"No location header after login: {error_text}")
        next_url = response.headers['location']
        response = self.client.get(next_url, headers={"referer": response.url},
                                   allow_redirects=False,
                                   name=urlsplit(next_url).path)

        query = parse_qs(urlsplit(response.headers['location']).query)
        headers = {'content-type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}

        data = {
            'grant_type': 'authorization_code',
            'code': query['code'][0],
            'redirect_uri': os.getenv('IDP_REDIRECT_URI', 'http://localhost:8000/oauth2/login/')
        }
        if code_verifier:
            data['code_verifier'] = code_verifier

        auth = None
        client_secret = os.getenv('IDP_CLIENT_SECRET')
        if client_secret:
            client_id = os.getenv('IDP_CLIENT_ID', 'ec1e39cb-e3e7-46c7-87b7-70ace4165d13')
            auth = (client_id, client_secret)

        response = self.client.post(
            urlsplit(config['token_endpoint']).path, data=urlencode(data, doseq=True), headers=headers, auth=auth,
            name=urlsplit(config['token_endpoint']).path)
        content = json.loads(response.text)

        headers = {
            'accept': 'application/json',
            'authorization': '%s %s' % (content['token_type'], content['access_token'])
        }
        self.client.get(urlsplit(config['userinfo_endpoint']).path, headers=headers)
        self.client.get(f"{urlsplit(config['end_session_endpoint']).path}?id_token_hint={content['id_token']}",
                        name=urlsplit(config['end_session_endpoint']).path)


# if launched directly, e.g. "python3 debugging.py", not "locust -f debugging.py"
if __name__ == "__main__":
    website_user = WebsiteUser
    website_user.host = os.getenv('HOST')

    run_single_user(website_user)
