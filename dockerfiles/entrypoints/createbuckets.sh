#!/bin/sh

# Exit if we are not initializing the setup
test "${INIT}" || exit 0

/usr/src/app/docker/wait-for-it.sh storage:9000 --timeout=30 --strict
/usr/local/bin/rc alias set myrustfs http://storage:9000 "$RUSTFS_ROOT_USER" "$RUSTFS_ROOT_PASSWORD";
/usr/local/bin/rc bucket create -p myrustfs/static;
/usr/local/bin/rc bucket anonymous set download myrustfs/static;
/usr/local/bin/rc bucket create -p myrustfs/media;
/usr/local/bin/rc bucket anonymous set download myrustfs/media;
/usr/local/bin/rc bucket create -p myrustfs/build-tools;
/usr/local/bin/rc bucket anonymous set download myrustfs/build-tools;
/usr/local/bin/rc bucket create -p myrustfs/builds;
/usr/local/bin/rc bucket anonymous set download myrustfs/builds;
/usr/local/bin/rc bucket create -p myrustfs/usercontent;
/usr/local/bin/rc bucket anonymous set download myrustfs/usercontent;
/usr/local/bin/rc bucket create -p myrustfs/build-uploads;
exit 0;
