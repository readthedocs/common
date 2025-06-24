#!/bin/sh

# Exit if we are not initializing the setup
test "${INIT}" || exit 0

/usr/src/app/docker/wait-for-it.sh storage:9000 --timeout=30 --strict
/usr/bin/mc alias set myminio http://storage:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD";
/usr/bin/mc mb myminio/static;
/usr/bin/mc policy set public myminio/static;
/usr/bin/mc mb myminio/media;
/usr/bin/mc policy set public myminio/media;
/usr/bin/mc mb myminio/build-tools;
/usr/bin/mc policy set public myminio/build-tools;
/usr/bin/mc mb myminio/builds;
/usr/bin/mc policy set public myminio/builds;
/usr/bin/mc mb myminio/usercontent;
/usr/bin/mc policy set public myminio/usercontent;
exit 0;

