.DEFAULT_GOAL := help

# =============================================================================
# Help Command
# =============================================================================

.PHONY: help
help: ## Show this help
	@awk -f scripts/help.awk $(MAKEFILE_LIST)

# =============================================================================
# Python Environment
# =============================================================================

pip: ## Install python dependencies
	pip install -r requirements.dev.txt

## Real Device Test Commands ##

list-devices: ## Check real device IDs (Requires SWITCHBOT_TOKEN/SECRET)
	@set -a; [ -f .env ] && . ./.env; set +a; \
	if [ -z "$$SWITCHBOT_TOKEN" ] || [ -z "$$SWITCHBOT_SECRET" ]; then \
		echo "ERROR: SWITCHBOT_TOKEN or SWITCHBOT_SECRET is not set."; \
		echo "  Please create .env file or export them."; \
		exit 1; \
	fi; \
	cd services/exporter && \
	docker build -q -t switchbot-exporter:latest . && \
	docker run --rm \
		-e SWITCHBOT_TOKEN="$$SWITCHBOT_TOKEN" \
		-e SWITCHBOT_SECRET="$$SWITCHBOT_SECRET" \
		switchbot-exporter:latest \
		python scripts/list_devices.py

run-real: ## Run Exporter in real mode (Requires SWITCHBOT_TOKEN/SECRET)
	@set -a; [ -f .env ] && . ./.env; set +a; \
	if [ -z "$$SWITCHBOT_TOKEN" ] || [ -z "$$SWITCHBOT_SECRET" ]; then \
		echo "ERROR: SWITCHBOT_TOKEN or SWITCHBOT_SECRET is not set."; \
		echo "  Please create .env file or export them."; \
		exit 1; \
	fi; \
	cd services/exporter && \
	SWITCHBOT_TOKEN="$$SWITCHBOT_TOKEN" \
	SWITCHBOT_SECRET="$$SWITCHBOT_SECRET" \
	USE_MOCK=false \
	COLLECTION_INTERVAL=10 \
	LOG_LEVEL=INFO \
	docker compose up --build

## Docker Commands for SwitchBot Exporter ##

docker-build-exporter: ## Build Docker image (multi-arch supported)
	cd services/exporter && docker build -t switchbot-exporter:latest .

docker-run-exporter: ## Run exporter container
	cd services/exporter && docker compose up switchbot-exporter

docker-dev: ## Start development environment (with Prometheus)
	cd services/exporter && docker compose --profile monitoring up -d

docker-test-exporter: ## Run local tests
	cd services/exporter && docker build -t switchbot-exporter:test . && \
	docker run --rm -e SWITCHBOT_TOKEN=test -e SWITCHBOT_SECRET=test switchbot-exporter:test python -m pytest

docker-down: ## Stop and remove containers
	cd services/exporter && docker compose down

docker-buildx-exporter: ## Multi-arch build (for production)
	cd services/exporter && docker buildx build \
		--platform linux/amd64,linux/arm64 \
		-t switchbot-exporter:multiarch \
		--push .

docker-logs: ## Monitor logs
	cd services/exporter && docker compose logs -f switchbot-exporter

## Kubernetes Commands ##

k8s-secret-generate: ## Generate K8s secret from .env
	@echo "🔐 Generating Kubernetes secret from .env..."
	@if [ ! -f .env ]; then \
		echo "❌ Error: .env file not found!"; \
		echo "💡 Please copy the example: cp .env.example .env"; \
		echo "💡 Then edit .env with your actual SwitchBot credentials"; \
		exit 1; \
	fi
	@source .env && \
	SWITCHBOT_TOKEN_BASE64=$$(printf '%s' "$$SWITCHBOT_TOKEN" | base64) && \
	SWITCHBOT_SECRET_BASE64=$$(printf '%s' "$$SWITCHBOT_SECRET" | base64) && \
	sed -e "s/{{SWITCHBOT_TOKEN_BASE64}}/$$SWITCHBOT_TOKEN_BASE64/g" \
	    -e "s/{{SWITCHBOT_SECRET_BASE64}}/$$SWITCHBOT_SECRET_BASE64/g" \
	    k8s/overlays/production/secret.template.yaml > k8s/overlays/production/secret.yaml
	@echo "✅ secret.yaml generated successfully!"
	@echo "🚀 You can now run: kubectl apply -k k8s/overlays/production"

k8s-secret-clean: ## Clean up generated Kubernetes files
	@echo "🧹 Cleaning up generated Kubernetes files..."
	@rm -f k8s/overlays/production/secret.yaml
	@rm -f k8s/overlays/production/minio-secret.yaml
	@rm -f k8s/overlays/production/openobserve-secret.yaml
	@echo "✅ Cleanup completed!"

k8s-deploy-mock: ## Deploy mock environment
	@echo "🧪 Deploying mock environment..."
	kubectl apply -k k8s/overlays/mock
	@echo "✅ Mock environment deployed!"
	@echo "📊 Check status: kubectl get pods -n smart-home"

k8s-deploy-production: k8s-secret-generate ## Deploy production environment (auto-generates secret.yaml)
	@echo "🚀 Deploying production environment..."
	kubectl apply -k k8s/overlays/production
	@echo "✅ Production environment deployed!"
	@echo "📊 Check status: kubectl get pods -n smart-home"

.PHONY: pip list-devices run-real docker-build-exporter docker-run-exporter docker-dev docker-test-exporter docker-down docker-buildx-exporter docker-logs k8s-secret-generate k8s-secret-clean k8s-deploy-mock k8s-deploy-production
