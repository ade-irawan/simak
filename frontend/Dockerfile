# syntax=docker/dockerfile:1
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY . .
# Sub-path publik (mis. /simak); kosong = akar. Ditanam saat build, ubah lalu build ulang.
ARG BASE_PATH=
ENV BASE_PATH=$BASE_PATH
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
