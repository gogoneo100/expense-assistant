FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and timezone support (Asia/Taipei)
ENV TZ=Asia/Taipei
ENV PYTHONUNBUFFERED=1

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

# Default exposed port (overridden by $PORT on PaaS)
EXPOSE 8080

# Run entry point with unbuffered output
CMD ["python", "-u", "run.py"]

