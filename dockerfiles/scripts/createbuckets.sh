#!/bin/bash
if [ -n "$INIT" ];
then
    export AWS_ACCESS_KEY_ID=admin
    export AWS_SECRET_ACCESS_KEY=password
    export AWS_DEFAULT_REGION=us-east-1

    for BUCKET in static media build-tools
    do
        aws --endpoint-url http://storage:9000 s3api create-bucket --acl public-read-write --bucket $BUCKET
    done
fi
