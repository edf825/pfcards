FROM python:alpine

ADD foundry*/ /app/
ADD pfcards /app/pfcards
ADD static /app/static
ADD setup.cfg pyproject.toml /app/

WORKDIR /app
RUN pip install -e .
