FROM python:slim
WORKDIR /opt/g10f/sso

ENV PYTHONUNBUFFERED 1

#https://docs.djangoproject.com/en/3.2/ref/contrib/gis/install/geolibs/
RUN apt-get update -y && apt-get -y install binutils libproj19 gdal-bin && apt-get clean

COPY requirements-docker.txt .
RUN pip install -U pip && pip install -U wheel && pip install -r requirements-docker.txt
COPY apps apps
WORKDIR /opt/g10f/sso/apps
RUN python manage.py collectstatic
CMD ["run.sh"]
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
# CMD ["gunicorn", "sso.wsgi:application"]
EXPOSE 8000
