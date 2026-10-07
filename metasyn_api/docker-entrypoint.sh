#!/bin/bash
# Runs the API and the UI in one container; stops both when either exits or on SIGTERM.
set -u

# Several API processes so a long fit does not make the API unavailable.
uvicorn main:app --host 0.0.0.0 --port 8000 --workers "${API_WORKERS:-2}" &
# The UI only waits on the API, so threads let many slow requests share a worker.
# The timeout matches TIMEOUT in frontend/app_flask.py (fitting large files can be slow).
gunicorn --chdir frontend --bind 0.0.0.0:5000 --workers 2 --worker-class gthread --threads 8 --timeout 300 app_flask:app &

stop() { kill $(jobs -p) 2>/dev/null; }
trap 'stop; exit 0' TERM INT

wait -n
code=$?
stop
wait
exit $code
