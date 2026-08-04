FROM python:3.9-slim

ARG SPIDERFOOT_REF=b9c345de5b085debc7444fc10e0e26e7745df5f2

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates gcc git libffi-dev libjpeg62-turbo-dev libxml2-dev libxslt1-dev \
    && git clone https://github.com/smicallef/spiderfoot.git /opt/spiderfoot \
    && git -C /opt/spiderfoot checkout "$SPIDERFOOT_REF" \
    && python -m pip install --no-cache-dir --upgrade "pip<24" "setuptools<69" "wheel" "Cython<3" \
    && python -m pip install --no-cache-dir --no-build-isolation "PyYAML==5.4.1" \
    && python -m pip install --no-cache-dir -r /opt/spiderfoot/requirements.txt \
    && useradd --create-home --uid 1000 spiderfoot \
    && mkdir -p /var/lib/spiderfoot/log /var/lib/spiderfoot/cache \
    && chown -R spiderfoot:spiderfoot /opt/spiderfoot /var/lib/spiderfoot \
    && apt-get purge -y gcc git libffi-dev libjpeg62-turbo-dev libxml2-dev libxslt1-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

ENV SPIDERFOOT_DATA=/var/lib/spiderfoot \
    SPIDERFOOT_LOGS=/var/lib/spiderfoot/log \
    SPIDERFOOT_CACHE=/var/lib/spiderfoot/cache \
    PYTHONDONTWRITEBYTECODE=1
USER spiderfoot
WORKDIR /opt/spiderfoot
ENTRYPOINT ["python", "sf.py"]
CMD ["-h"]
