FROM node:18.15
COPY package.json /usr/src/app/packages/addons-inject/
WORKDIR /usr/src/app/packages/addons-inject/
RUN npm install -g --install-links --omit dev
ENV PATH="$PATH:/usr/local/lib/node_modules/@readthedocs/addons-inject/node_modules/.bin"
CMD ["wrangler", "dev"]
