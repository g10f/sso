# Build stage: installs the Python packages into /venv. All packages come as wheels with their libraries
# included; build-essential is only there for a package that has no wheel for the platform.
FROM python:3.14.9-slim AS build

RUN set -ex \
    && apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt
COPY requirements /requirements
RUN python3 -m venv /venv \
    && /venv/bin/pip install --no-cache-dir -r /requirements.txt


FROM python:3.14.9-slim

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
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user
RUN groupadd --gid $USER_GID $USERNAME && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# The venv and the code belong to root. The user only writes the media files and, with collectstatic
# (also in the theme images), the static files.
RUN mkdir -p /opt/g10f/sso/htdocs/media /opt/g10f/sso/htdocs/static \
    && chown $USERNAME:$USERNAME /opt/g10f/sso/htdocs/media /opt/g10f/sso/htdocs/static

WORKDIR /opt/g10f/sso/apps
COPY apps .

USER $USERNAME
RUN ./manage.py collectstatic --noinput
ENTRYPOINT ["./docker-entrypoint.sh"]
# Which peers gunicorn accepts X-Forwarded-* from. The default stays "*", because
# the proxy address is not known in advance (in kubernetes the health probes come
# from the node, the ingress from a pod ip). As an environment variable rather
# than a command line flag it survives an args override in the helm chart, and a
# deployment that does know its proxy can pin it to an address or network.
ENV FORWARDED_ALLOW_IPS="*"
# Start gunicorn
CMD ["gunicorn", "sso.wsgi:application", "-b", "0.0.0.0:8000"]
EXPOSE 8000
