#! /bin/sh

npm install

$(npm bin)/webpack-dev-server \
  --mode=development \
  --host=0.0.0.0 \
  --port=10001
