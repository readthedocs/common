#! /bin/sh

if [ -n "${DOCKER_NPM_CI}" ]; then
    echo "Installing all NPM dependencies"
    npm ci
fi

$(npm bin)/webpack-dev-server \
  --mode=development \
  --host=0.0.0.0 \
  --port=10001
