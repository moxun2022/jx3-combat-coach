# syntax=docker/dockerfile:1
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir . && useradd --create-home coach && mkdir /data && chown coach:coach /data
ENV JX3_DATABASE_PATH=/data/combat-coach.sqlite3
USER coach
EXPOSE 8000
CMD ["uvicorn", "jx3_combat_coach.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
