# recon 하니스: python + adb + frida-tools.
# 빌드 컨텍스트는 리포 루트(docker-compose.yml 에서 context: . 지정).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        android-tools-adb \
        wget \
        xz-utils \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /work
