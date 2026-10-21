#! /bin/bash

../../docker/common.sh

# When a task is revoked, it still needs to be picked up by a worker to "delete it",
# in the meantime celery will keep those revoked tasks in memory,
# if you restart celery, that list is lost, and the tasks will be executed after a worker picks it up.
# We need to save that state in a file so isn't lost.
# Ref https://docs.celeryq.dev/en/stable/userguide/workers.html#persistent-revokes.
CELERY_STATE_DIR=/var/run/celery/
mkdir -p $CELERY_STATE_DIR
CMD="uv run python3 -m celery --quiet --app=${CELERY_APP_NAME}.worker worker --optimization=fair --concurrency=1 --queues=builder,celery,default,build01,build:default,build:large --loglevel=${CELERY_LOG_LEVEL} --statedb=${CELERY_STATE_DIR}worker.state --without-mingle --without-gossip --without-heartbeat"

if [ -n "${DOCKER_NO_RELOAD}" ]; then
  echo "Running process with no reload"
  $CMD
else
  echo "Running process with reload"
  nodemon --config ../nodemon.json --exec "$CMD"
fi
