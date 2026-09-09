# Deployed to Railway as its own service ("docs") — a plain static site, no build step.
# ENV PORT is only a local-dev fallback: Railway injects its own at runtime, and the
# official nginx image's docker-entrypoint auto-renders default.conf.template through
# envsubst on every container start, substituting just that one variable.
FROM nginx:alpine

ENV PORT=8080

COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY *.html /usr/share/nginx/html/
COPY style.css /usr/share/nginx/html/style.css

EXPOSE 8080
