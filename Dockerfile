FROM python:alpine

ADD . /app
WORKDIR /app
RUN pip install -e .