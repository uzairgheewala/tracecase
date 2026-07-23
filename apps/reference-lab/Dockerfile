FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY apps/reference-lab/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY apps/reference-lab /app
EXPOSE 8010
CMD ["python", "manage.py", "runserver", "0.0.0.0:8010"]
