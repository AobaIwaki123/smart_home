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

k8s-deploy-production: k8s-secret-generate ## Deploy production environment (auto-generates secret.yaml)
	@echo "🚀 Deploying production environment..."
	kubectl apply -k k8s/overlays/production
	@echo "✅ Production environment deployed!"
	@echo "📊 Check status: kubectl get pods -n smart-home"

.PHONY: pip list-devices run-real docker-build-exporter docker-run-exporter docker-dev docker-test-exporter docker-down docker-buildx-exporter docker-logs docker-build-dummy docker-run-dummy docker-down-dummy docker-logs-dummy k8s-secret-generate k8s-secret-clean k8s-deploy-production
