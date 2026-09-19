# Built with the REPOSITORY ROOT as the context: the Railway service points at this file with
# the RAILWAY_DOCKERFILE_PATH variable rather than a root directory, so no config file sits at
# the repo root where another service might read it.
FROM node:22-alpine AS build
WORKDIR /app
COPY website/package.json website/package-lock.json ./
RUN npm ci
COPY website/ ./
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/dist ./dist
COPY website/server.mjs ./server.mjs
CMD ["node", "server.mjs"]
