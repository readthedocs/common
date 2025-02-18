#! /bin/sh

../../docker/common.sh

if [ -n "$INIT" ];
then
    echo "Performing initial tasks..."
    ../../docker/createbuckets.sh
    uv run python3 manage.py migrate
    uv run python3 manage.py migrate --database telemetry
    cat ../../docker/createsuperuser.py | uv run python3 manage.py shell
    uv python3 manage.py collectstatic --no-input
    uv run python3 manage.py loaddata test_data
fi

CMD="uv run gunicorn readthedocs.wsgi:application -w 3 -b 0.0.0.0:8000 --max-requests=10000 --timeout=0"

if [ -n "${DOCKER_NO_RELOAD}" ]; then
  echo "Running process with no reload"
  $CMD
else
  echo "Running process with reload"
  nodemon --config ../nodemon.json --exec "${CMD}"
fi
