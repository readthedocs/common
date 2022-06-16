#! /bin/sh

../../docker/common.sh

python3 ../../docker/scripts/wait_for_search.py

CMD="python3 -m celery -A ${CELERY_APP_NAME}.worker worker -Ofair -c 2 -Q web,web01,reindex,autoscaling -l DEBUG"

if [ -n "${DOCKER_NO_RELOAD}" ]; then
  echo "Running Docker with no reload"
  $CMD
else
  echo "Running Docker with reload"
  nodemon --config ../nodemon.json --exec $CMD
fi
