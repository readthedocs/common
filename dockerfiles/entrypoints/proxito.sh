#! /bin/sh

../../docker/common.sh

CMD="python3 manage.py runserver --noreload 0.0.0.0:8000"

if [ -n "${DOCKER_NO_RELOAD}" ]; then
  echo "Running process with no reload"
  $CMD
else
  echo "Running process with reload"
  nodemon --config ../nodemon.json --exec $CMD
fi
