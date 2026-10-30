SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE ?= docker compose
API     := $(COMPOSE) exec -T api
RUN_PY  := $(COMPOSE) run --rm --no-deps -T worker
# Same, but writing files owned by you (generated data, reports).
RUN_PY_AS_ME := $(COMPOSE) run --rm --no-deps -T --user "$$(id -u):$$(id -g)" worker
SEED    ?= 42

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

.env:
	@cp .env.example .env
	@sed -i.bak \
		-e "s|^APP_KEY=.*|APP_KEY=base64:$$(openssl rand -base64 32)|" \
		-e "s|^DB_PASSWORD=.*|DB_PASSWORD=$$(openssl rand -hex 16)|" \
		-e "s|^S3_ACCESS_KEY=.*|S3_ACCESS_KEY=$$(openssl rand -hex 10)|" \
		-e "s|^S3_SECRET_KEY=.*|S3_SECRET_KEY=$$(openssl rand -hex 20)|" \
		-e "s|^DEMO_USER_PASSWORD=.*|DEMO_USER_PASSWORD=$$(openssl rand -hex 6)|" \
		.env && rm -f .env.bak
	@echo "Created .env with random local secrets."

.PHONY: env
env: .env ## Create .env with random secrets (only if missing)

.PHONY: up
up: .env ## Build and start the whole stack (waits until healthy)
	$(COMPOSE) up -d --build --wait
	@echo "Dashboard: $$(grep ^APP_URL .env | cut -d= -f2)"

.PHONY: down
down: ## Stop the stack (keeps data)
	$(COMPOSE) down

.PHONY: reset
reset: ## Stop the stack and delete all data volumes and generated files
	$(COMPOSE) down -v --remove-orphans
	rm -rf data/synthetic

.PHONY: seed
seed: ## Generate the synthetic condominiums, ingest them and run the audit
	@mkdir -p data
	$(RUN_PY_AS_ME) condo-audit synth generate --out /data/synthetic --seed $(SEED)
	$(API) php artisan demo:seed /data/synthetic --wait

.PHONY: demo
demo: up seed eval ## up + seed + eval: the 5-minute tour
	@echo; echo "Open $$(grep ^APP_URL .env | cut -d= -f2) and log in as $$(grep ^DEMO_USER_EMAIL .env | cut -d= -f2) / $$(grep ^DEMO_USER_PASSWORD .env | cut -d= -f2)"

.PHONY: eval
eval: ## Precision/recall of the audit against the planted ground truth
	$(RUN_PY) condo-audit eval --ground-truth /data/synthetic/ground_truth.json

.PHONY: report
report: ## Write the Markdown audit report of the demo condominium to data/report.md
	$(RUN_PY_AS_ME) condo-audit report --condominium residencial-jardim-das-acacias --out /data/report.md

.PHONY: test
test: test-api test-pipeline ## Run every test suite inside the containers

.PHONY: test-api
test-api: ## PHPUnit (API)
	$(API) vendor/bin/phpunit

.PHONY: test-pipeline
test-pipeline: ## pytest (pipeline), including integration tests against the test database
	$(API) sh -c 'DB_DATABASE=condo_audit_test php artisan migrate --force --no-interaction'
	$(RUN_PY) sh -c 'DATABASE_URL=$${DATABASE_URL%/*}/condo_audit_test pytest -q -p no:cacheprovider --cov'

.PHONY: lint
lint: ## Static analysis and formatting checks for both services
	$(API) vendor/bin/pint --test
	$(API) vendor/bin/phpstan analyse --memory-limit=1G --no-progress
	$(RUN_PY) ruff check src tests
	$(RUN_PY) ruff format --check src tests
	$(RUN_PY) mypy

.PHONY: logs
logs: ## Follow API and worker logs
	$(COMPOSE) logs -f api worker
