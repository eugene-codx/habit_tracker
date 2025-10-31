#!/bin/bash

echo "Applying migrations ..."
alembic upgrade head

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${UVICORN_PORT:-8000}
