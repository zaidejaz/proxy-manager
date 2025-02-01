FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry

COPY poetry.lock pyproject.toml ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

COPY . .

ENV FLASK_APP=proxy_manager
ENV FLASK_ENV=production

CMD ["poetry", "run", "flask", "run", "--host=0.0.0.0"]
