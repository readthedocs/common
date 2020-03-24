#! /bin/bash

../../docker/common.sh

CMD="python3 -m celery worker -A ${CELERY_APP_NAME}.worker -Ofair -c 2 -Q builder,celery,default,build01 -l DEBUG"

if [ -n "${DOCKER_NO_RELOAD}" ]; then
  echo "Running Docker with no reload"
  $CMD
else
  echo "Running Docker with reload"
  watchmedo auto-restart \
  --patterns="readthedocs/*.py" \
  --patterns="readthedocsinc/*.py" \
  --ignore-patterns="*.#*.py" \
  --ignore-patterns="*.pyo" \
  --ignore-patterns="*.pyc" \
  --ignore-patterns="*flycheck*.py" \
  --ignore-patterns="*test*" \
  --ignore-patterns="*migrations*" \
  --ignore-patterns="*management/commands*" \
  --ignore-directories \
  --recursive \
  --signal=SIGTERM \
  --kill-after=5 \
  --interval=5 \
  -- \
  $CMD
fi
