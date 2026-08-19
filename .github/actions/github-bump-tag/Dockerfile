FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293
LABEL "repository"="https://github.com/UKHSA-Internal/devops-github-actions"
LABEL "homepage"="https://github.com/UKHSA-Internal/devops-github-actions"

RUN apk --no-cache add bash git curl jq && npm install -g semver

COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
