FROM python:slim
WORKDIR /opt/g10f/sso

ENV PYTHONUNBUFFERED 1

RUN apt-get update -y
#https://docs.djangoproject.com/en/3.2/ref/contrib/gis/install/geolibs/
RUN apt-get -y install binutils libproj-dev gdal-bin

# psycopg2
# RUN apt-get -y install gcc libpq-dev

COPY requirements-docker.txt .
RUN python -m pip install -U pip
RUN pip install -r requirements-docker.txt
COPY apps apps
WORKDIR /opt/g10f/sso/apps
# RUN ./manage.py collectstatic
# CMD ["./manage.py", "runserver"]
CMD ["gunicorn", "sso.wsgi:application"]
EXPOSE 8000
# EXPOSE 11211
