#! /bin/bash

../../docker/common.sh

CELERY_STATE_DIR=/var/run/celery/
mkdir -p $CELERY_STATE_DIR
CMD="python3 -m celery -A ${CELERY_APP_NAME}.worker worker -Ofair -c 1 -Q builder,celery,default,build01,build:default,build:large -l DEBUG --statedb=${CELERY_STATE_DIR}worker.state"

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
  --interval=5 \
  -- \
  $CMD
fi
