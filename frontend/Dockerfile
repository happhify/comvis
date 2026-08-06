# Build context = repo root (lihat docker-compose.yml) supaya bisa
# COPY docker/nginx/nginx.conf di stage kedua.

FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
# vite build default mode "production" -> .env.development (VITE_API_BASE_URL)
# TIDAK ikut terbaca, jadi BASE_URL di api.js jatuh ke "" (relatif, lewat nginx).
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
