FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and timezone support (Asia/Taipei)
ENV TZ=Asia/Taipei
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persistent storage for SQLite database and data
VOLUME ["/app/data"]

# Default exposed ports (8080 for local, 10000 for Render)
EXPOSE 8080
EXPOSE 10000

# Run entry point with unbuffered output
CMD ["python", "-u", "run.py"]

