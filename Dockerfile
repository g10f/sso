# Build stage: installs the Python packages into /venv. Only psycopg-c is compiled from source,
# the other packages come as wheels with their libraries included.
FROM python:3.14.10-slim AS build

RUN set -ex \
    && apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt /requirements.txt
RUN python3 -m venv /venv \
    && /venv/bin/pip install --no-cache-dir -r /requirements.txt


FROM python:3.14.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Runtime packages: libpq5 for psycopg, gdal-bin for GeoDjango (pulls in libgdal, libgeos and libproj),
# media-types for the mimetypes module, postgresql-client and procps for working in the container
RUN set -ex \
    && apt-get update && apt-get install -y --no-install-recommends gdal-bin libpq5 media-types postgresql-client procps \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /venv /venv

ARG USERNAME=worker
ARG PROJ_NAME=sso
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user. Keep the uid at 1000: files and volumes mounted from the host belong to it.
RUN groupadd --gid $USER_GID $USERNAME && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# The venv and the code belong to root. The user only writes the media files and, with collectstatic
# (also in images built on top of this one), the static files.
RUN mkdir -p /opt/g10f/$PROJ_NAME/htdocs/media /opt/g10f/$PROJ_NAME/htdocs/static \
    && chown $USERNAME:$USERNAME /opt/g10f/$PROJ_NAME/htdocs/media /opt/g10f/$PROJ_NAME/htdocs/static

WORKDIR /opt/g10f/$PROJ_NAME/apps
COPY apps .

ENV DJANGO_SETTINGS_MODULE=sso.settings

USER $USERNAME
# Some settings refuse to start without SECRET_KEY; collectstatic doesn't use it, so a dummy value is enough.
RUN SECRET_KEY=collectstatic-only ./manage.py collectstatic --noinput

ENTRYPOINT ["./docker-entrypoint.sh"]

# Which peers gunicorn accepts X-Forwarded-* from. "*" because the address of the proxy in front of the
# container is not known in advance (in kubernetes, for example, the health probes come from the node and the
# ingress from a pod ip). As an environment variable rather than a command line flag it survives an overridden
# command, and a deployment that does know its proxy can pin it to an address or network.
ENV FORWARDED_ALLOW_IPS="*"
# Start gunicorn
CMD ["gunicorn", "sso.wsgi:application", "-b", "0.0.0.0:8000"]
EXPOSE 8000
