# syntax=docker/dockerfile:1.7
# Multi-stage. Final image targets < 100MB by stripping dev deps and using alpine.
# Used for CI runners and bundled "ai-shell" containers — most users will install via npm.

# ---- Stage 1: build ----
FROM node:20-alpine AS build
WORKDIR /src

# Native deps (keytar uses node-gyp). Required only at build for prebuilds resolution.
RUN apk add --no-cache python3 make g++ libsecret-dev

COPY package.json package-lock.json* ./
# Install with full devDeps so we can run tsup. --ignore-scripts skips keytar postinstall here;
# the runtime stage installs production deps fresh and pulls the right prebuild.
RUN npm install --no-audit --no-fund --ignore-scripts

COPY tsconfig.json tsup.config.ts ./
COPY src ./src
RUN npm run build

# ---- Stage 2: production deps ----
FROM node:20-alpine AS deps
WORKDIR /app
RUN apk add --no-cache libsecret
COPY package.json package-lock.json* ./
RUN npm install --omit=dev --no-audit --no-fund

# ---- Stage 3: runtime ----
FROM node:20-alpine AS runtime
LABEL org.opencontainers.image.source="https://github.com/openrouter-example/openrouter"
LABEL org.opencontainers.image.title="openrouter-cli"
LABEL org.opencontainers.image.description="OpenRouter CLI"
WORKDIR /app

# libsecret is the keytar backend on Linux; without it the encrypted-file fallback kicks in.
RUN apk add --no-cache libsecret ca-certificates tini \
 && addgroup -S openrouter && adduser -S openrouter -G openrouter

COPY --from=deps  /app/node_modules ./node_modules
COPY --from=build /src/dist        ./dist
COPY --from=build /src/package.json ./package.json

USER openrouter
ENV NODE_ENV=production
ENTRYPOINT ["/sbin/tini", "--", "node", "/app/dist/cli.js"]
CMD ["--help"]
