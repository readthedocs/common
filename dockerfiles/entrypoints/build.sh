#! /bin/bash

../../docker/common.sh

python3 -m celery worker -A ${CELERY_APP_NAME}.worker -Ofair -c 2 -Q builder,celery,default,build01 -l DEBUG
