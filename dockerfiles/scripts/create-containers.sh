#! /bin/sh

if [ -n "$INIT" ];
then
    CONNECTION_STRING="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://storage:10000/devstoreaccount1"
    az storage container create --connection-string $CONNECTION_STRING --public-access "blob" --name "builds"
    az storage container create --connection-string $CONNECTION_STRING --public-access "blob" --name "media"
    az storage container create --connection-string $CONNECTION_STRING --public-access "blob" --name "static"
    az storage container create --connection-string $CONNECTION_STRING --public-access "blob" --name "envs"

    az storage cors add --connection-string $CONNECTION_STRING --origins '*' --services 'b' --methods GET OPTIONS HEAD --allowed-headers '*'
fi
