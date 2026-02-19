# Multi-architecture SwitchBot Exporter
# Supports both arm64 (Apple Silicon/RaspberryPi) and x86_64 (Intel/AMD)
FROM python:3.13-slim

# メタデータラベル（Docker Hub等での識別用）
LABEL maintainer="SwitchBot Exporter"
LABEL description="Prometheus exporter for SwitchBot API metrics"
LABEL version="1.0.0"

# システムパッケージのアップデート（セキュリティ重要）
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pythonの出力をバッファリングしない（ログの即座表示）
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 依存関係を先にコピー&インストール（Docker層キャッシュの最適化）
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ソースコードのコピー
COPY src/ ./src/

# ユーティリティスクリプトのコピー
COPY scripts/ ./scripts/

# デバイス設定ファイルのコピー
COPY devices.json .

# 非特権ユーザーの作成（セキュリティのベストプラクティス）
RUN useradd -m -u 1001 -s /bin/bash exporter-user && \
    chown -R exporter-user:exporter-user /app

# 非特権ユーザーに切り替え
USER exporter-user

# ヘルスチェック用のエンドポイント公開
EXPOSE 8000

# アプリケーション開始時間の診断用
ENV START_TIME=""

# 適切なシグナルハンドリングのためのエントリポイント
CMD ["python", "-u", "src/main.py"]