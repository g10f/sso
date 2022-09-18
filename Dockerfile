FROM python:3.10 as builder
WORKDIR /opt/g10f/sso

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV='/venv'
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt .
COPY requirements requirements
RUN python3 -m venv $VIRTUAL_ENV
RUN pip install -U pip wheel
RUN pip install -r requirements.txt

#####################################################
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV='/venv'
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

#https://docs.djangoproject.com/en/3.2/ref/contrib/gis/install/geolibs/
RUN apt-get update -y && apt-get -y install binutils libproj19 gdal-bin && apt-get clean

COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
WORKDIR /opt/g10f/sso/apps
COPY apps .
COPY Docker/gunicorn.conf.py ./gunicorn.conf.py
ARG SECRET_KEY=dummy
RUN ./manage.py collectstatic
ENTRYPOINT ["./docker-entrypoint.sh"]

# Start gunicorn
CMD ["gunicorn", "sso.wsgi:application", "--bind 0.0.0.0:8000", "-w", "2"]
EXPOSE 8000
