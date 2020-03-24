#! /bin/sh

../../docker/common.sh

python3 ../../docker/scripts/wait_for_search.py

python3 -m celery worker -A ${CELERY_APP_NAME}.worker -Ofair -c 2 -Q web,web01,reindex -l DEBUG
