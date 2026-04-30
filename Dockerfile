FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt /app/requirements.txt
COPY messenger_bot_api-2.0.5-py3-none-any.whl /app/messenger_bot_api-2.0.5-py3-none-any.whl

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir /app/messenger_bot_api-2.0.5-py3-none-any.whl \
    && pip install --no-cache-dir -r /app/requirements.txt

# Копируем код проекта
COPY . /app

# Создаем директории хранения файлов
RUN mkdir -p /app/storage/input /app/storage/output /app/storage/temp

CMD ["python", "-m", "app.main"]