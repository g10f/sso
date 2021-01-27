FROM python
RUN apt-get update
RUN apt-get install -y postgis postgresql memcached
WORKDIR /opt/g10f/sso
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY apps apps
WORKDIR /opt/g10f/sso/apps
RUN ./manage.py collectstatic
CMD ["./manage.py", "runserver"]
# CMD ["gunicorn", "sso.wsgi:application"]
EXPOSE 8000
EXPOSE 11211
