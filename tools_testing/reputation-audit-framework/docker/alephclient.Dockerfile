FROM python:3.11-slim

RUN python -m pip install --no-cache-dir "alephclient==2.7.0" \
    && useradd --create-home --uid 1000 aleph

USER aleph
WORKDIR /home/aleph
ENTRYPOINT ["alephclient"]
CMD ["--help"]
