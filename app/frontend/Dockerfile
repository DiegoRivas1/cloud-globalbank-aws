FROM nginx:1.27-alpine

# Hosts de los servicios; en Kubernetes se sobreescriben (backend-service, etc.)
ENV BACKEND_HOST=backend BACKEND_PORT=3000 \
    LOADGEN_HOST=loadgen LOADGEN_PORT=8000

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY index.html style.css app.js /usr/share/nginx/html/
COPY vendor/ /usr/share/nginx/html/vendor/

EXPOSE 80
