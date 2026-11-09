FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_PATH=/tmp/banco_local.db

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py db.py service.py ./

# Buenas prácticas: no ejecutar como root
RUN useradd --uid 10001 --no-create-home appuser
USER 10001

EXPOSE 3000
CMD ["gunicorn", "-b", "0.0.0.0:3000", "-w", "2", "--threads", "4", "--timeout", "30", "main:create_app()"]