FROM nginxinc/nginx-unprivileged:stable-alpine
USER root
RUN apk upgrade --no-cache \
    && apk add --no-cache 'pcre2>=10.49-r0'
COPY index.html /usr/share/nginx/html/index.html
COPY nginx.conf /etc/nginx/conf.d/default.conf
USER nginx
EXPOSE 8080
