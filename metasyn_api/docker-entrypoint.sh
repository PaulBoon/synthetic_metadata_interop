#!/bin/bash
# Runs the API and the UI in one container; stops both when either exits or on SIGTERM.
set -u

uvicorn main:app --host 0.0.0.0 --port 8000 &
# The timeout matches TIMEOUT in frontend/app_flask.py (fitting large files can be slow).
gunicorn --chdir frontend --bind 0.0.0.0:5000 --workers 2 --timeout 300 app_flask:app &

stop() { kill $(jobs -p) 2>/dev/null; }
trap 'stop; exit 0' TERM INT

wait -n
code=$?
stop
wait
exit $code
