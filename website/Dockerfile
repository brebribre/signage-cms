# Built with this folder as the context (the Railway service's root directory is /website),
# so nothing outside the site is in scope.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/dist ./dist
COPY server.mjs ./server.mjs
CMD ["node", "server.mjs"]
