#! /bin/sh

../../docker/common.sh

CMD="python3 -m celery -A ${CELERY_APP_NAME}.worker beat -l ${CELERY_LOG_LEVEL}"

# Not sure why, but the db becomes corrupted at some point
# and make the startup of this process to fail.
# Removing it makes Celery to re-create it.
rm -f celerybeat-schedule.db

if [ -n "${DOCKER_NO_RELOAD}" ]; then
  echo "Running process with no reload"
  $CMD
else
  echo "Running process with reload"
  nodemon --config ../nodemon.json --exec $CMD
fi
