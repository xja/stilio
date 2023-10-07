FROM python:3.8-slim-buster

ENV PYTHONUNBUFFERED=1
ENV ROOT=/usr/src/app

WORKDIR ${ROOT}

COPY stilio/config.py stilio/config.py
COPY stilio/__init__.py stilio/__init__.py
COPY stilio/crawler stilio/crawler
COPY stilio/persistence stilio/persistence

RUN pip install poetry
COPY pyproject.toml .
COPY poetry.lock .
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-dev
RUN rm -rf /pyproject.toml \
    && rm -rf /poetry.lock

COPY docker/crawler/entrypoint.sh entrypoint.sh
RUN sed -i 's/\r$//g' entrypoint.sh

ENTRYPOINT ["bash", "entrypoint.sh"]

CMD ["python", "-m", "stilio.crawler.main"]
