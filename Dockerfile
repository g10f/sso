FROM python:slim
WORKDIR /proj/sso/
COPY apps src
COPY requirements.txt .
RUN pip install -r requirements.txt
EXPOSE 8080

