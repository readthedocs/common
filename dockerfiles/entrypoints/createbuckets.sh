#!/bin/sh

# Exit if we are not initializing the setup
test "${INIT}" || exit 0

/usr/src/app/docker/wait-for-it.sh storage:9000 --timeout=30 --strict
/usr/bin/mc alias set myrustfs http://storage:9000 "$RUSTFS_ROOT_USER" "$RUSTFS_ROOT_PASSWORD";
/usr/bin/mc mb myrustfs/static;
/usr/bin/mc policy set public myrustfs/static;
/usr/bin/mc mb myrustfs/media;
/usr/bin/mc policy set public myrustfs/media;
/usr/bin/mc mb myrustfs/build-tools;
/usr/bin/mc policy set public myrustfs/build-tools;
/usr/bin/mc mb myrustfs/builds;
/usr/bin/mc policy set public myrustfs/builds;
/usr/bin/mc mb myrustfs/usercontent;
/usr/bin/mc policy set public myrustfs/usercontent;
exit 0;

