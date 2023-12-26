FROM python:3.12 as builder

RUN apt-get update && apt-get -y install --no-install-recommends python3-venv binutils libproj25 gdal-bin && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/g10f/sso

ENV PYTHONDONTWRITEBYTECODE=1
ENV VIRTUAL_ENV='/venv'
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt .
COPY requirements requirements
RUN python3 -m venv $VIRTUAL_ENV
RUN pip install -U pip wheel
RUN pip install -r requirements.txt

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
