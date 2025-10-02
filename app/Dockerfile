# Build stage
FROM python:3.13 AS builder
WORKDIR /app
COPY requirements.txt ./

RUN pip install --no-cache-dir \
    --timeout=200 \
    --retries=5 \
    -r requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.13-bookworm
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "src.main"]