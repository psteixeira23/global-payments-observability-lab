FROM nginx:1.27-alpine

RUN apk add --no-cache openssl \
    && mkdir -p /etc/nginx/certs \
    && openssl req -x509 -newkey rsa:2048 \
      -keyout /etc/nginx/certs/dev.key \
      -out /etc/nginx/certs/dev.crt \
      -days 3650 -nodes \
      -subj "/CN=localhost/O=global-payments-observability-lab/C=US" \
    && chown -R nginx:nginx /etc/nginx /var/cache/nginx /var/log/nginx /var/run

COPY nginx.conf /etc/nginx/nginx.conf

USER nginx
EXPOSE 8088 8443

CMD ["nginx", "-g", "daemon off;"]
