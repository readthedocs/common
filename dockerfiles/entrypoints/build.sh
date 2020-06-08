#! /bin/bash

../../docker/common.sh

CMD="python3 -m celery worker -A ${CELERY_APP_NAME}.worker -Ofair -c 1 -Q builder,celery,default,build01,build:default,build:large -l DEBUG"

if [ -n "${DOCKER_NO_RELOAD}" ]; then
  echo "Running Docker with no reload"
  $CMD
else
  echo "Running Docker with reload"
  watchmedo auto-restart \
  --patterns="./readthedocs/*.py;./readthedocsinc/*.py" \
  --ignore-patterns="*.#*.py;*.pyo;*.pyc;*flycheck*.py;*test*;*migrations*;*management/commands*" \
  --ignore-directories \
  --recursive \
  --signal=SIGTERM \
  --kill-after=5 \
  --interval=5 \
  -- \
  $CMD
fi
