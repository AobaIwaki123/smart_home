pip:
	pip install -r requirements.dev.txt

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

.PHONY: pip docker-build-exporter docker-run-exporter docker-dev docker-test-exporter docker-down docker-buildx-exporter docker-logs