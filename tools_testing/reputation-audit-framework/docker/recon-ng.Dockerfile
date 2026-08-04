FROM python:3.11-slim

ARG RECON_NG_REF=c08acee0f84645ecf521ec616ac2dde94cbc1d63
ARG RECON_MODULES_REF=9527714d2bb38886422bab5f1c4724d4a20d3057

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && git clone https://github.com/lanmaster53/recon-ng.git /opt/recon-ng \
    && git -C /opt/recon-ng checkout "$RECON_NG_REF" \
    && python -m pip install --no-cache-dir -r /opt/recon-ng/REQUIREMENTS \
    && git clone https://github.com/lanmaster53/recon-ng-modules.git /opt/recon-ng-modules \
    && git -C /opt/recon-ng-modules checkout "$RECON_MODULES_REF" \
    && useradd --create-home --uid 1000 recon \
    && mkdir -p /home/recon/.recon-ng/modules/import \
        /home/recon/.recon-ng/modules/reporting \
        /home/recon/.recon-ng/modules/recon/domains-hosts \
        /home/recon/.recon-ng/workspaces \
    && cp /opt/recon-ng-modules/modules/import/list.py /home/recon/.recon-ng/modules/import/list.py \
    && cp /opt/recon-ng-modules/modules/reporting/json.py /home/recon/.recon-ng/modules/reporting/json.py \
    && cp /opt/recon-ng-modules/modules/recon/domains-hosts/certificate_transparency.py \
        /home/recon/.recon-ng/modules/recon/domains-hosts/certificate_transparency.py \
    && cp /opt/recon-ng-modules/modules/recon/domains-hosts/hackertarget.py \
        /home/recon/.recon-ng/modules/recon/domains-hosts/hackertarget.py \
    && chown -R recon:recon /home/recon \
    && rm -rf /opt/recon-ng-modules /var/lib/apt/lists/*

ENV HOME=/home/recon PYTHONDONTWRITEBYTECODE=1
USER recon
WORKDIR /opt/recon-ng
ENTRYPOINT ["python", "/opt/recon-ng/recon-cli"]
CMD ["--help"]
