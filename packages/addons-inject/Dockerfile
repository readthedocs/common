FROM node:18.15
COPY package.json /usr/src/app/packages/addons-inject/
COPY index.js /usr/src/app/packages/addons-inject/
COPY wrangler.toml /usr/src/app/packages/addons-inject/
WORKDIR /usr/src/app/packages/addons-inject/
RUN npm install --omit dev
ENTRYPOINT ["node_modules/.bin/wrangler", "dev"]
