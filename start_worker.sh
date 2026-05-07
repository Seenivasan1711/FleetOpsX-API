#!/bin/bash
# Celery worker entrypoint for Render Web Service.
# Starts a minimal HTTP server to satisfy Render's port binding check,
# then runs the Celery worker in the foreground.
python3 -m http.server "${PORT:-8080}" &
exec celery -A app.workers.celery_app worker --loglevel=info
