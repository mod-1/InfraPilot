FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git && apt-get clean

COPY infrastructure_api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

WORKDIR /app/infrastructure_api

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "core.wsgi:application"]