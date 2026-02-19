pip:
	pip install -r requirements.dev.txt

# =============================================================================
# Real Device Test Commands
# =============================================================================

# 実機の deviceId を確認するスクリプトを実行（要: SWITCHBOT_TOKEN / SWITCHBOT_SECRET）
list-devices:
	@if [ -z "$$SWITCHBOT_TOKEN" ] || [ -z "$$SWITCHBOT_SECRET" ]; then \
		echo "ERROR: 環境変数が未設定です。以下を実行してください:"; \
		echo "  export SWITCHBOT_TOKEN='your_token'"; \
		echo "  export SWITCHBOT_SECRET='your_secret'"; \
		exit 1; \
	fi
	cd services/exporter && \
	docker build -q -t switchbot-exporter:latest . && \
	docker run --rm \
		-e SWITCHBOT_TOKEN="$$SWITCHBOT_TOKEN" \
		-e SWITCHBOT_SECRET="$$SWITCHBOT_SECRET" \
		switchbot-exporter:latest \
		python scripts/list_devices.py

# 実機モードで Exporter を起動（要: SWITCHBOT_TOKEN / SWITCHBOT_SECRET）
run-real:
	@if [ -z "$$SWITCHBOT_TOKEN" ] || [ -z "$$SWITCHBOT_SECRET" ]; then \
		echo "ERROR: 環境変数が未設定です。以下を実行してください:"; \
		echo "  export SWITCHBOT_TOKEN='your_token'"; \
		echo "  export SWITCHBOT_SECRET='your_secret'"; \
		exit 1; \
	fi
	cd services/exporter && \
	SWITCHBOT_TOKEN="$$SWITCHBOT_TOKEN" \
	SWITCHBOT_SECRET="$$SWITCHBOT_SECRET" \
	USE_MOCK=false \
	COLLECTION_INTERVAL=10 \
	LOG_LEVEL=INFO \
	docker compose up

# =============================================================================
# Docker Commands for SwitchBot Exporter
# =============================================================================

# Dockerイメージのビルド（マルチアーキ対応）
docker-build-exporter:
	cd services/exporter && docker build -t switchbot-exporter:latest .

# 軽量テスト実行（Exporter単体）
docker-run-exporter:
	cd services/exporter && docker compose up switchbot-exporter

# 開発環境起動（Prometheus付き）
docker-dev:
	cd services/exporter && docker compose --profile monitoring up -d

# ローカルテスト実行
docker-test-exporter:
	cd services/exporter && docker build -t switchbot-exporter:test . && \
	docker run --rm -e SWITCHBOT_TOKEN=test -e SWITCHBOT_SECRET=test switchbot-exporter:test python -m pytest

# コンテナ停止・削除
docker-down:
	cd services/exporter && docker compose down

# マルチアーキビルド（本番用）
docker-buildx-exporter:
	cd services/exporter && docker buildx build \
		--platform linux/amd64,linux/arm64 \
		-t switchbot-exporter:multiarch \
		--push .

# ログ監視
docker-logs:
	cd services/exporter && docker compose logs -f switchbot-exporter

# =============================================================================
# Kubernetes Commands
# =============================================================================

# k8s/.env ファイルからsecret.yamlを自動生成
k8s-secret-generate:
	@echo "🔐 Generating Kubernetes secret from k8s/.env..."
	@if [ ! -f k8s/.env ]; then \
		echo "❌ Error: k8s/.env file not found!"; \
		echo "💡 Please copy the example: cp k8s/.env.example k8s/.env"; \
		echo "💡 Then edit k8s/.env with your actual SwitchBot credentials"; \
		exit 1; \
	fi
	@source k8s/.env && \
	SWITCHBOT_TOKEN_BASE64=$$(echo -n "$$SWITCHBOT_TOKEN" | base64) && \
	SWITCHBOT_SECRET_BASE64=$$(echo -n "$$SWITCHBOT_SECRET" | base64) && \
	sed -e "s/{{SWITCHBOT_TOKEN_BASE64}}/$$SWITCHBOT_TOKEN_BASE64/g" \
	    -e "s/{{SWITCHBOT_SECRET_BASE64}}/$$SWITCHBOT_SECRET_BASE64/g" \
	    k8s/overlays/production/secret.template.yaml > k8s/overlays/production/secret.yaml
	@echo "✅ secret.yaml generated successfully!"
	@echo "🚀 You can now run: kubectl apply -k k8s/overlays/production"

# K8s環境のクリーンアップ（secret.yamlも削除）
k8s-clean:
	@echo "🧹 Cleaning up generated Kubernetes files..."
	@rm -f k8s/overlays/production/secret.yaml
	@echo "✅ Cleanup completed!"

# モック環境のデプロイ
k8s-deploy-mock:
	@echo "🧪 Deploying mock environment..."
	kubectl apply -k k8s/overlays/mock
	@echo "✅ Mock environment deployed!"
	@echo "📊 Check status: kubectl get pods -n smart-home"

# 本番環境のデプロイ（secret.yamlを自動生成）
k8s-deploy-production: k8s-secret-generate
	@echo "🚀 Deploying production environment..."
	kubectl apply -k k8s/overlays/production
	@echo "✅ Production environment deployed!"
	@echo "📊 Check status: kubectl get pods -n smart-home"

.PHONY: pip list-devices run-real docker-build-exporter docker-run-exporter docker-dev docker-test-exporter docker-down docker-buildx-exporter docker-logs k8s-secret-generate k8s-clean k8s-deploy-mock k8s-deploy-production