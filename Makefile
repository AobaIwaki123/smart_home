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

k8s-secret-generate: ## Generate all K8s secrets from .env (SwitchBot + Tailscale)
	@echo "🔐 Generating Kubernetes secrets from .env..."
	@if [ ! -f .env ]; then \
		echo "❌ Error: .env file not found!"; \
		echo "💡 Please copy the example: cp .env.example .env"; \
		exit 1; \
	fi
	@source .env && \
	SWITCHBOT_TOKEN_BASE64=$$(printf '%s' "$$SWITCHBOT_TOKEN" | base64) && \
	SWITCHBOT_SECRET_BASE64=$$(printf '%s' "$$SWITCHBOT_SECRET" | base64) && \
	sed -e "s/{{SWITCHBOT_TOKEN_BASE64}}/$$SWITCHBOT_TOKEN_BASE64/g" \
	    -e "s/{{SWITCHBOT_SECRET_BASE64}}/$$SWITCHBOT_SECRET_BASE64/g" \
	    k8s/secret/switchbot-secret.template.yaml > k8s/secret/switchbot-secret.yaml
	@source .env && \
	TAILSCALE_CLIENT_ID_BASE64=$$(printf '%s' "$$TAILSCALE_CLIENT_ID" | base64) && \
	TAILSCALE_CLIENT_SECRET_BASE64=$$(printf '%s' "$$TAILSCALE_CLIENT_SECRET" | base64) && \
	sed -e "s/{{TAILSCALE_CLIENT_ID_BASE64}}/$$TAILSCALE_CLIENT_ID_BASE64/g" \
	    -e "s/{{TAILSCALE_CLIENT_SECRET_BASE64}}/$$TAILSCALE_CLIENT_SECRET_BASE64/g" \
	    k8s/secret/tailscale-secret.template.yaml > k8s/secret/tailscale-secret.yaml
	@echo "✅ Secrets generated: k8s/secret/switchbot-secret.yaml, k8s/secret/tailscale-secret.yaml"

k8s-secret-clean: ## Clean up generated Kubernetes secret files
	@echo "🧹 Cleaning up generated secret files..."
	@rm -f k8s/secret/switchbot-secret.yaml
	@rm -f k8s/secret/tailscale-secret.yaml
	@echo "✅ Cleanup completed!"

k8s-tailscale-install: k8s-secret-generate ## Install/upgrade Tailscale Operator from .env
	@echo "🔧 Applying Tailscale namespace and secret..."
	kubectl create namespace tailscale --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -f k8s/secret/tailscale-secret.yaml
	@echo "🚀 Installing Tailscale Operator via Kustomize+Helm..."
	kustomize build --enable-helm k8s/base/tailscale | kubectl apply --server-side -f -
	@echo "✅ Tailscale Operator installed!"
	@echo "📊 Check status: kubectl get pods -n tailscale"

k8s-deploy-production: k8s-secret-generate ## Deploy production environment (auto-generates secrets)
	@echo "🚀 Deploying production environment..."
	kubectl apply -k k8s/overlays/production
	@echo "✅ Production environment deployed!"
	@echo "📊 Check status: kubectl get pods -n smart-home"

.PHONY: pip list-devices run-real docker-build-exporter docker-run-exporter docker-dev docker-test-exporter docker-down docker-buildx-exporter docker-logs docker-build-dummy docker-run-dummy docker-down-dummy docker-logs-dummy k8s-secret-generate k8s-secret-clean k8s-tailscale-install k8s-deploy-production
