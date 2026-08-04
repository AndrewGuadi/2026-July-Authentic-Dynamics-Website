# syntax=docker/dockerfile:1
# reputation-audit-framework — passive OSINT audit runner
FROM python:3.11-slim AS base

ARG DOCKER_GID=989

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    RAF_IN_CONTAINER=1

# Native collectors and sibling-container runtime.
#  - libimage-exiftool-perl : ExifTool module (native execution)
#  - docker-cli             : sibling-container execution for Amass/SpiderFoot/Blackbird
#
# wkhtmltopdf is not available in Debian Trixie. PDF output remains optional;
# the container always produces the canonical Markdown and JSON reports.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        libimage-exiftool-perl \
        docker-cli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

# Optional: install Maigret natively so the container works without a Docker socket.
ARG INSTALL_MAIGRET=true
RUN if [ "$INSTALL_MAIGRET" = "true" ]; then python -m pip install "maigret==0.6.3" || \
      echo "maigret install skipped (docker execution will be used)"; fi

COPY core/ ./core/
COPY modules/ ./modules/
COPY normalization/ ./normalization/
COPY integrations/ ./integrations/
COPY reporting/ ./reporting/
COPY main.py config.yaml config.maigret-only.yaml config.all-integrations.yaml config.smoke.yaml config.adapter-smoke.yaml config.amass-smoke.yaml ./

RUN mkdir -p /app/output /app/images \
    && useradd --create-home --uid 1000 auditor \
    && docker_group="$(getent group "${DOCKER_GID}" | cut -d: -f1)" \
    && if [ -z "$docker_group" ]; then groupadd --gid "${DOCKER_GID}" dockerhost; docker_group=dockerhost; fi \
    && usermod --append --groups "$docker_group" auditor \
    && chown -R auditor:auditor /app \
    && if [ -d /usr/local/lib/python3.11/site-packages/maigret/resources ]; then \
         chown -R auditor:auditor /usr/local/lib/python3.11/site-packages/maigret/resources; \
       fi

USER auditor

ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
