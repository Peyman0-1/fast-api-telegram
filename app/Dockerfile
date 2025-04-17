FROM sunpeek/poetry:py3.11-slim as builder

WORKDIR /app

COPY . /app

RUN poetry install --no-root

#apply migrations into database
RUN alembic upgrade head

FROM sunpeek/poetry:py3.11-slim

WORKDIR /app

COPY --from=builder /app /app
EXPOSE 8000
CMD [ "python", "src/main.py" ]