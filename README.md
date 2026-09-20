# SSO

SSO is an **OpenID Connect Identity Provider** with built-in user and organisation
management. It implements OAuth2 / OpenID Connect (authorization code with PKCE,
implicit, hybrid, client credentials and refresh token grants), multi-factor
authentication (TOTP and WebAuthn / FIDO2), and exposes its user and organisation
data through a JSON-LD / Hydra REST API.

It is a [Django](https://www.djangoproject.com/) application and is distributed as a
Docker image (`ghcr.io/g10f/sso`) and a Helm chart.

- **Version:** 5.4.8
- **Runtime:** Python 3.12+ (the official image is built on Python 3.14), Django 5.2,
  PostgreSQL with PostGIS
- **License:** BSD-style, see [LICENSE](LICENSE)

## Features

- **OpenID Connect Provider** with discovery (`/.well-known/openid-configuration`),
  JWKS, UserInfo, token introspection (RFC 7662) and revocation (RFC 7009) endpoints.
- **OAuth2 grants:** authorization code (with PKCE, RFC 7636), implicit, hybrid,
  client credentials and refresh token.
- **Signing key rotation** – RSA signing keys are created and rotated automatically
  (`manage.py rotate_signing_keys`).
- **Multi-factor authentication:** TOTP (authenticator apps) and WebAuthn / FIDO2
  (security keys, fingerprint, Windows Hello). MFA can be required for admins.
- **Stateless sessions** stored in signed JWT cookies.
- **User & organisation management:** users, organisations, admin regions, countries,
  country groups and associations, including geo-coordinates (PostGIS).
- **JSON-LD / Hydra API** (`/api/`) with v1 and v2 user endpoints, organisation,
  region, country and application-role resources.
- **Self-registration**, access requests, e-mail confirmation and account recovery.
- **Internationalisation** – ships with translations for ~15 languages.
- **Theming** via a pluggable `SSO_THEME` app.

## Application layout

The Django project lives under `apps/`. The main packages are:

| Package | Responsibility |
| --- | --- |
| `sso.accounts` | User model, profiles, application roles, membership |
| `sso.organisations` | Organisations, admin regions, countries, associations (PostGIS) |
| `sso.oauth2` | OAuth2 / OpenID Connect provider, tokens, signing keys |
| `sso.auth` | Login, TOTP and WebAuthn devices, one-time-password middleware |
| `sso.api` | JSON-LD / Hydra REST API (v1 and v2) |
| `sso.registration` | Self-registration and admin registration workflow |
| `sso.access_requests` | Requesting and extending access to organisations |
| `sso.emails` | Managed e-mail addresses and forwarding |
| `sso.impersonate` | Superuser "log in as" another user |
| `l10n` | Countries, currencies and localisation data |

## Quick start with Docker

```bash
docker compose up
```

This starts the SSO app (http://localhost:8000), a PostGIS database and an nginx
container serving uploaded media (http://localhost:8080). The compose file creates a
superuser `admin` / `admin` and loads the initial fixtures.

> The values in `docker-compose.yml` (`SECRET_KEY=123`, `admin/admin`,
> `SSO_USE_HTTPS=False`) are for local development only. **Do not** use them in
> production.

## Run locally (development server)

All `manage.py` commands are run from the `apps/` directory:

```bash
cd apps
./manage.py runserver
```

With SSL (via `runserver_plus` from `django-extensions`; install
`requirements-dev.txt` for `django-extensions`, `Werkzeug` and `pyOpenSSL`):

```python
# apps/sso/settings/local_settings.py
INSTALLED_APPS = INSTALLED_APPS + ['django_extensions']
SSO_USE_HTTPS = True
SSO_DOMAIN = "localhost:8443"
```

```bash
cd apps
./manage.py runserver_plus localhost:8443 --cert-file ../temp/cert
```

## Kubernetes with Helm

[Helm](https://helm.sh) must be installed (see the
[Helm documentation](https://helm.sh/docs)).

```bash
helm repo add g10f https://g10f.github.io/helm-charts
helm repo update            # if the repo was already added earlier
helm install my-sso g10f/sso
helm delete my-sso          # to uninstall
```

## Prepare a development environment

1. Install Python 3.12+.
2. Create a virtualenv: `python3 -m venv venv`
3. Activate it: `source venv/bin/activate`
4. Update pip: `pip install -U pip`
5. Install requirements: `pip install -r requirements.txt`
   (use `requirements-dev.txt` for the test/dev tooling).
6. Install PostgreSQL and PostGIS: `sudo apt install postgresql postgis`
7. Enable the required extensions on `template1`:
   ```bash
   sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS citext;" template1
   sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS postgis;" template1
   ```
8. Create the database user and database:
   ```bash
   sudo -u postgres psql -c "CREATE USER sso CREATEDB PASSWORD 'sso'"
   sudo -u postgres psql -c 'CREATE DATABASE sso OWNER sso'
   ```
9. Change into the app directory: `cd apps`
10. Create the tables: `./manage.py migrate`
11. Create a superuser: `./manage.py createsuperuser`
12. Start the development server: `./manage.py runserver`

## Running the tests

The test tooling (Selenium, locust, etc.) is listed in `requirements-dev.txt`:

```bash
pip install -r requirements-dev.txt
```

For the Selenium tests you also need a matching `chromedriver` on your `PATH`
(see `chrome-driver.sh`). Run the suite with:

```bash
cd apps
./manage.py test
```

## Management commands

| Command | Description |
| --- | --- |
| `rotate_signing_keys` | Create / rotate the OAuth2 signing keys |
| `cleartokens` | Delete expired authorization codes and refresh tokens |
| `cleanupregistration` | Remove expired self-registration profiles |
| `clean_access_requests` | Remove obsolete access requests |
| `cleanup_users` | Clean up inactive / unconfirmed users |
| `clear_unconfirmed_emails` | Remove unconfirmed e-mail addresses |
| `create_permissions` | Create the custom permissions |
| `add_role` | Add an application role |
| `update_user_language` | Bulk-update the users' language |
| `migrate_pictures` | Re-process stored user pictures |
| `user_count` | Print the number of users (used by the Docker entrypoint) |
| `update_location` / `update_timezone` | Recompute organisation geo data |

## Configuration

Configuration is done through environment variables (see
`apps/sso/settings/defaults.py`). A `local_settings.py` next to the settings module is
loaded if present and can override anything.

### Core

| Name | Default | Description |
| --- | --- | --- |
| `SECRET_KEY` | *(random per start)* | Django secret key – **set this in production** |
| `DEBUG` | `False` | Django debug mode |
| `ALLOWED_HOSTS` | `''` | Comma-separated additional allowed hosts |
| `FORWARDED_ALLOW_IPS` | `*` | Peers gunicorn accepts `X-Forwarded-Proto`/`-Ssl` from, which determine whether `request.is_secure()` is true. Pin it to the proxy address or network wherever that is known. |
| `SSO_DOMAIN` | `localhost:8000` | Public domain of the service |
| `SSO_USE_HTTPS` | `True` | Whether the service is served over HTTPS |
| `SSO_SITE_NAME` | `G10F` | Displayed site name |
| `ROOT_URLCONF` | `sso.urls` | Root URL configuration |
| `SSO_THEME` | `None` | Optional theme app prepended to `INSTALLED_APPS` |
| `SSO_STYLE` | `css/main.min.css` | Stylesheet |
| `SSO_DEFAULT_THEME` | `auto` | Default UI theme (`auto`/`light`/`dark`) |

### Database, cache & Celery

| Name | Default | Description |
| --- | --- | --- |
| `DATABASE_NAME` | `sso` | Database name |
| `DATABASE_USER` | `sso` | Database user |
| `DATABASE_PASSWORD` | `sso` | Database password |
| `DATABASE_HOST` | `localhost` | Database host |
| `DATABASE_CONN_MAX_AGE` | `60` | Persistent connection lifetime (without pooling) |
| `DATABASE_CONN_POOL` | `False` | Enable psycopg connection pooling |
| `CACHES_LOCATION` | `None` | Memcached location(s), comma-separated |
| `CELERY_BROKER_URL` | `None` | Celery broker URL |
| `CELERY_BROKER_USE_SSL` | `True` | Use SSL for the Celery broker |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | `2621440` | Max upload size in bytes (2.5 MB) |

### E-mail

| Name | Default | Description |
| --- | --- | --- |
| `EMAIL_HOST` | `localhost` | SMTP host |
| `EMAIL_PORT` | `25` | SMTP port |
| `DEFAULT_FROM_EMAIL` | `gunnar.scherf@gmail.com` | Default sender |
| `SSO_NOREPLY_EMAIL` | `gunnar.scherf@gmail.com` | No-reply sender |
| `SERVER_EMAIL` | `root@localhost` | Error-report sender |
| `EMAIL_SUBJECT_PREFIX` | `[SSO] ` | Subject prefix |
| `SSO_ASYNC_EMAILS` | `False` | Send e-mails asynchronously via Celery |

### Authentication, MFA & security

| Name | Default | Description |
| --- | --- | --- |
| `REGISTRATION_OPEN` | `False` | Allow public self-registration |
| `SSO_PASSWORD_MINIMUM_LENGTH` | `8` | Minimum password length |
| `SESSION_COOKIE_AGE` | `1209600` | Session lifetime in seconds (2 weeks) |
| `SSO_LOGIN_MAX_AGE` | `300` | Max age of the signed login step (seconds) |
| `SSO_ADMIN_MAX_AGE` | `1800` | Re-auth interval for admin pages (30 min) |
| `SSO_ADMIN_ONLY_MFA` | `False` | Only admins may use MFA |
| `SSO_ADMIN_MFA_REQUIRED` | `False` | Require MFA for admins |
| `SSO_TOTP_TOLERANCE` | `2` | Accepted TOTP time-step window |
| `SSO_WEBAUTHN_VERSION` | `FIDO_2_0` | WebAuthn version (`U2F_V2` / `FIDO_2_0`) |
| `SSO_WEBAUTHN_USER_VERIFICATION` | `discouraged` | WebAuthn user verification requirement |
| `SSO_WEBAUTHN_AUTHENTICATOR_ATTACHMENT` | `''` | WebAuthn authenticator attachment |
| `SSO_WEBAUTHN_EXTENSIONS` | `False` | Enable WebAuthn extensions |
| `SSO_WEBAUTHN_CREDPROPS` | `False` | Enable WebAuthn credProps extension |
| `SSO_REFRESH_TOKEN_AGE` | `7776000` | Refresh token lifetime (90 days) |
| `SSO_THROTTLING_DURATION` | `30` | Login throttling window (seconds) |
| `SSO_THROTTLING_MAX_CALLS` | `5` | Max login attempts per window |
| `SSO_RECAPTCHA_ENABLED` | `True` | Enable reCAPTCHA on registration |
| `RECAPTCHA_PUBLIC_KEY` / `RECAPTCHA_PRIVATE_KEY` | *(Google test keys)* | reCAPTCHA keys – set your own |
| `SSO_2FA_HELP_URL` | `''` | External 2FA help page |

### Media, storage & misc

| Name | Default | Description |
| --- | --- | --- |
| `STATIC_ROOT` | `../htdocs/static` | Static files root |
| `MEDIA_ROOT` | `../htdocs/media` | Uploaded media root |
| `STATIC_URL` | `/static/` | Static URL prefix |
| `MEDIA_URL` | `/media/` | Media URL prefix |
| `SSO_USER_MAX_PICTURE_SIZE` | `1048576` | Max user picture size in bytes (1 MB) |
| `SSO_USER_PICTURE_REQUIRED` | `False` | Require a profile picture |
| `SSO_GOOGLE_GEO_API_KEY` | `None` | Google Geocoding API key |
| `SSO_ORGANISATION_EMAIL_DOMAIN` | `''` | Domain for managed organisation e-mails |
| `SSO_ABOUT` | `https://g10f.de/` | "About" redirect target |
| `SSO_DATA_PROTECTION_URI` | `None` | Privacy policy URL |
| `SSO_ENABLE_PLAUSIBLE` | `False` | Enable Plausible analytics |
| `ANALYTICS_CODE` | `''` | Analytics snippet |
| `LOGGING_LEVEL_ROOT` / `LOGGING_LEVEL_SSO` / `LOGGING_LEVEL_DJANGO` / `LOGGING_LEVEL_DB` | `INFO` | Log levels |

## API

The API entry point is `/api/` and follows the JSON-LD / Hydra conventions. Highlights:

- `GET /api/v2/users/`, `GET /api/v2/users/me/`, `GET/PUT/DELETE /api/v2/users/{uuid}/`
- `GET /api/v2/organisations/`, `/api/v2/regions/`, `/api/v2/countries/`,
  `/api/v2/country_groups/`, `/api/v2/associations/`
- `GET /api/v2/apps/` and per-user application roles under
  `/api/v2/users/{uuid}/apps/{app_uuid}/roles/`
- OpenID Connect endpoints under `/oauth2/` (`authorize`, `token`, `userinfo`,
  `jwks`, `introspect`, `revoke`) plus discovery at
  `/.well-known/openid-configuration`.

## Changelog

the entries below list the notable changes per minor release. See the git
history for the full list of patch releases.

### 5.4 (current, 5.4.8)
- security fix: the `chained_filter` endpoint is restricted to the chained fields,
  closing an unauthenticated data-exposure hole
- security fix: refresh tokens are bound to the client they were issued to, and
  authorization codes expire after `SSO_AUTHORIZATION_CODE_AGE`
- security fix: stored XSS in the admin through `mark_safe` on user-supplied data
- security fix: the login throttle can no longer be bypassed with a spoofed
  `X-Forwarded-For` or a random query string, and accounts behind a shared IP no
  longer throttle each other
- security fix: an OAuth2 error raised before the request was validated is no
  longer reported to an unregistered `redirect_uri` (open redirect)
- standard-conform OpenID Connect UserInfo endpoint
- `is_primary` flag for organisation membership when a user belongs to more than one
- Instagram page for organisations (Google+ removed)

### 5.3
- Django 5.2 LTS maintenance (up to 5.2.17), Python 3.14 base image
- security hardening: constant-time secret comparison, `client_secret_post` support
  advertised in the discovery metadata, removed padding from the JWS header
- resolved Django 6.0 deprecation warnings

### 5.1 – 5.2
- oauthlib 3.3.1, Bootstrap 5.3.7, fido2 2.0
- "Implicit flow" selectable in the client self-service, client `state` field
  raised to 4096 characters
- info logging for TOTP

### 5.0
- Django 5.2 compatibility

### 4.6 – 4.8
- Django 5.0 and 5.1 compatibility
- list of available apps added to the API

### 4.0 – 4.5
- Django 4.0 – 4.2 compatibility, psycopg 3, Python 3.12
- access-request workflow extended (app id / message, expiry cleanup command,
  e-mail on denial)
- django-reversion integration and superuser impersonation
- new (invisible) reCAPTCHA, `get_random_secret_key` fallback for `SECRET_KEY`
- configurable TOTP tolerance, external 2FA help page, WebAuthn user-verification
  setting and default theme configurable via environment

### 3.3.23
- fido2 version 1.1
- switched to Fido2 only
- fixed iOS compatibility

### 3.2.0
- support for WebAuthn, allows usb-keys, fingerprint and windows hello

### 3.1.4
- Docker support

### 3.0.1
- django 3.1 compatibility
- automatically create and change the signature keys with
  `./manage.py rotate_signing_keys`
- new settings with the following defaults:
  - `SSO_ACCESS_TOKEN_AGE = 60 * 60`  (1 hour)
  - `SSO_ID_TOKEN_AGE = 60 * 5`  (5 minutes)
  - `SSO_SIGNING_KEYS_VALIDITY_PERIOD = 60 * 60 * 24 * 30`  (30 days)

### 2.1.0
- django 2.2 compatibility
- oauthlib >= 3
- new UserNote model
- application specific scopes to restrict the clients which have access to user
  application roles
- key/value table to store arbitrary user attributes (UI/forms overridable via settings)
- new select box for administration of user application roles
- support `post_logout_redirect_uri` of the OIDC spec

### 1.3.1
- user organisations are stored through an explicit membership class/table

### 1.3.0
- PKCE support

### 1.2.1
- Django 2.0 compatibility

### 1.2.0
- organisation data management

### 1.1.0
- JSON-LD / Hydra API

### 1.0.0
- OAuth2 and OpenID Connect support
