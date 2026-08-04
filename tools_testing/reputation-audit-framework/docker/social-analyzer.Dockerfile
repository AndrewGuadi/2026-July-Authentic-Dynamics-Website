FROM python:3.11-slim

RUN python -m pip install --no-cache-dir "social-analyzer==0.45" \
    && useradd --create-home --uid 1000 analyzer

USER analyzer
WORKDIR /home/analyzer
ENTRYPOINT ["python", "-m", "social-analyzer"]
CMD ["--help"]
