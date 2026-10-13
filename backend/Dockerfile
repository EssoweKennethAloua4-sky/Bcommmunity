FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN adduser --disabled-password --gecos "" app
WORKDIR /app
RUN chown app:app /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app . .
RUN mkdir -p /app/media && chown app:app /app/media
RUN DJANGO_SECRET_KEY=build-only-secret-key-not-for-production \
    DATABASE_URL=postgresql://build:build@127.0.0.1/build \
    ALLOWED_HOSTS=localhost \
        python manage.py collectstatic --noinput \
    && chown -R app:app /app/staticfiles
USER app
EXPOSE 8000
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
