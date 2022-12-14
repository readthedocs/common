#! /bin/sh

../../docker/common.sh

if [ -n "$INIT" ];
then
    echo "Performing initial tasks..."
    ../../docker/createbuckets.sh
    python3 manage.py migrate
    python3 manage.py migrate --database telemetry
    cat ../../docker/createsuperuser.py | python3 manage.py shell
    python3 manage.py collectstatic --no-input
    python3 manage.py loaddata test_data
fi

CMD="python3 manage.py runserver --noreload 0.0.0.0:8000"

if [ -n "${DOCKER_NO_RELOAD}" ]; then
  echo "Running process with no reload"
  $CMD
else
  echo "Running process with reload"
  nodemon --config ../nodemon.json --exec $CMD
fi
