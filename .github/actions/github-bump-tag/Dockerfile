FROM node:20-alpine
LABEL "repository"="https://github.com/UKHSA-Internal/devops-github-actions"
LABEL "homepage"="https://github.com/UKHSA-Internal/devops-github-actions"

RUN apk --no-cache add bash git curl jq && npm install -g semver

COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
