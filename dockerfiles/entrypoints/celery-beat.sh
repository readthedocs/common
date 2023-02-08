#! /bin/sh

../../docker/common.sh

CMD="python3 -m celery -A ${CELERY_APP_NAME}.worker beat -l ${CELERY_LOG_LEVEL}"

if [ -n "${DOCKER_NO_RELOAD}" ]; then
  echo "Running process with no reload"
  $CMD
else
  echo "Running process with reload"
  nodemon --config ../nodemon.json --exec $CMD
fi
