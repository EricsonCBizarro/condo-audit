FROM node:22-alpine AS assets
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY vite.config.js ./
COPY resources ./resources
RUN npm run build

# serversideup/php: production-tuned PHP-FPM + Nginx, unprivileged user,
# runs migrations on boot when AUTORUN_ENABLED=true.
FROM serversideup/php:8.3-fpm-nginx-v3.5.2 AS base
ENV PHP_OPCACHE_ENABLE=1
WORKDIR /var/www/html

FROM base AS dev
COPY --chown=www-data:www-data composer.json composer.lock ./
RUN composer install --no-interaction --no-scripts --no-autoloader --prefer-dist
COPY --chown=www-data:www-data . .
COPY --from=assets --chown=www-data:www-data /app/public/build ./public/build
RUN composer dump-autoload --optimize

FROM base AS production
COPY --chown=www-data:www-data composer.json composer.lock ./
RUN composer install --no-interaction --no-scripts --no-autoloader --prefer-dist --no-dev
COPY --chown=www-data:www-data . .
COPY --from=assets --chown=www-data:www-data /app/public/build ./public/build
RUN composer dump-autoload --optimize --classmap-authoritative --no-dev
