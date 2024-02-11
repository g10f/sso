FROM python:3.12-slim-bookworm

# Install packages needed to run your application (not build deps):
ENV RUN_DEPS="libexpat1 libjpeg62-turbo libpcre3 libpq5 mime-support postgresql-client procps zlib1g libproj25 gdal-bin"
ENV BUILD_DEPS="build-essential curl git libexpat1-dev libjpeg62-turbo-dev libpcre3-dev libpq-dev zlib1g-dev libproj-dev"
RUN set -ex \
    && apt-get update && apt-get install -y --no-install-recommends $RUN_DEPS \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/g10f/sso

ENV PYTHONDONTWRITEBYTECODE=1
ENV VIRTUAL_ENV='/venv'
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt .
COPY requirements requirements
RUN set -ex \
    && apt-get update && apt-get install -y --no-install-recommends $BUILD_DEPS \
    && python3 -m venv ${VIRTUAL_ENV} \
    && pip install -U pip wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false $BUILD_DEPS \
    && rm -rf /var/lib/apt/lists/*

ARG USERNAME=worker
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user
RUN groupadd --gid $USER_GID $USERNAME && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# create media dir
RUN mkdir -p /opt/g10f/sso/htdocs/media
RUN chown $USERNAME:$USERNAME /opt/g10f/sso/htdocs/media

WORKDIR /opt/g10f/sso/apps
COPY apps .
COPY Docker/gunicorn.conf.py ./gunicorn.conf.py

RUN chown -R $USERNAME: $VIRTUAL_ENV
RUN chown -R $USERNAME: /opt/g10f

USER $USERNAME
ARG SECRET_KEY=dummy
RUN ./manage.py collectstatic
ENTRYPOINT ["./docker-entrypoint.sh"]
# Start gunicorn
CMD ["gunicorn", "sso.wsgi:application", "-b", "0.0.0.0:8000", "-w", "2"]
EXPOSE 8000
