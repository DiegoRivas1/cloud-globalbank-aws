FROM nginx:1.27-alpine

# Hosts de los servicios; en Kubernetes se sobreescriben (backend-service, etc.)
ENV BACKEND_ADDR=backend:3000 \
    LOADGEN_ADDR=loadgen:8000

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY index.html style.css app.js /usr/share/nginx/html/
COPY vendor/ /usr/share/nginx/html/vendor/

EXPOSE 80
