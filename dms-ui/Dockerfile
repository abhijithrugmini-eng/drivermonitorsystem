# Optional container path — the default POC workflow is `npm run dev` (see README.md).
# Use this when Docker Desktop is available and you want the dashboard running in a container.
#
# VITE_API_BASE_URL is baked in at build time (Vite env vars are client-side/static) — it must be
# a URL the *browser* can reach, not a docker-network service name. Override with:
#   docker compose build --build-arg VITE_API_BASE_URL=http://localhost:8000 ui

FROM node:20-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
