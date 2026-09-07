FROM python:3.12-slim

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates/ ./templates/
COPY static/ ./static/

RUN mkdir -p /data
ENV DATABASE_PATH=/data/baza.sqlite

EXPOSE 5000

CMD ["python", "app.py"]