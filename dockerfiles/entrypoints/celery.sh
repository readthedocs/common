#! /bin/sh

../../docker/common.sh

# If SEARCH is enabled, the celery container should wait for the search
# container to be ready
if [ "$SEARCH" != "" ]; then
  ../../docker/wait-for-it.sh search:9200 --timeout=360 --strict
fi

CMD="python3 -m celery -A ${CELERY_APP_NAME}.worker worker -Ofair -c 2 -Q web,web01,reindex,autoscaling -l DEBUG"

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
