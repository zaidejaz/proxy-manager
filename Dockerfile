FROM python:3.12-slim
WORKDIR /app

RUN pip install poetry
COPY poetry.lock pyproject.toml ./
RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction --no-ansi \
    && poetry add gunicorn gevent

COPY . .

ENV FLASK_APP=proxy_manager
ENV FLASK_ENV=production

# Using gevent worker for better concurrency
CMD ["poetry", "run", "gunicorn", \
     "--workers=6", \
     "--worker-class=gevent", \
     "--worker-connections=1000", \
     "--max-requests=10000", \
     "--max-requests-jitter=1000", \
     "--backlog=2048", \
     "--bind=0.0.0.0:5000", \
     "--timeout=30", \
     "proxy_manager:create_app()"]