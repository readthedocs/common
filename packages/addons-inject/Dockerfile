FROM node:18.15
COPY package.json /usr/src/app/packages/addons-inject/
WORKDIR /usr/src/app/packages/addons-inject/
RUN npm install -g --install-links --omit dev
ENTRYPOINT ["/usr/local/lib/node_modules/@readthedocs/addons-inject/node_modules/.bin/wrangler", "dev"]
