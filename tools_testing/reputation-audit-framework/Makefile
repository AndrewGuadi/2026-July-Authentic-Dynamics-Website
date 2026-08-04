.PHONY: help install doctor doctor-all run docker-build docker-build-all docker-pull docker-run entity-up smoke adapters-smoke tests clean

CLIENT ?= Sarah Mitchell
DOMAIN ?= sarahmitchellhomes.com
HANDLE ?= sarahmitchellrealtor
IMAGES ?= ./images

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "};{printf "  \033[32m%-14s\033[0m %s\n", $$1, $$2}'

install: ## One-command local install (venv + deps)
	@bash install.sh

doctor: ## Show which collectors are available locally
	@python main.py doctor

doctor-all: ## Check every requested integration in Docker
	@docker compose run --rm --no-deps audit doctor --config /app/config.all-integrations.yaml

run: ## Run an audit (override CLIENT/DOMAIN/HANDLE/IMAGES)
	@python main.py run --full-name "$(CLIENT)" --domain "$(DOMAIN)" \
		--username "$(HANDLE)" --image-dir "$(IMAGES)" --authorized yes

docker-build: ## Build the application image
	@docker compose build audit

docker-build-all: ## Build app plus custom collector/client images
	@docker compose --profile tools build audit social-analyzer recon-ng spiderfoot alephclient

docker-pull: ## Pull all collector images
	@docker compose --profile tools pull

docker-run: ## Run an audit inside the container
	@docker compose run --rm audit run --full-name "$(CLIENT)" --domain "$(DOMAIN)" \
		--username "$(HANDLE)" --image-dir "/app/images" --authorized yes

entity-up: ## Start the local OpenSanctions/yente service
	@docker compose --profile entity up -d yente-index yente

smoke: ## Run the bounded all-integration profile
	@docker compose run --rm --no-deps audit run --full-name "$(CLIENT)" --domain "$(DOMAIN)" \
		--username "$(HANDLE)" --image-dir "/app/images" --authorized yes \
		--config /app/config.smoke.yaml --no-pdf

adapters-smoke: ## Live-check SpiderFoot and Recon-ng adapters
	@docker compose run --rm --no-deps audit run --full-name "$(CLIENT) Adapter Verification" \
		--domain "$(DOMAIN)" --authorized yes --config /app/config.adapter-smoke.yaml --no-pdf

tests: ## Run contract and regression tests
	@python -m unittest discover -s tests -v

clean: ## Remove __pycache__ artefacts (evidence in output/ is never deleted)
	@find . -type d -name __pycache__ -prune -exec rm -rf {} + ; echo "cleaned"
