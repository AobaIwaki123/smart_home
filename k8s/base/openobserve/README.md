# OpenObserve (O2) - 可観測性プラットフォーム

スマートホーム監視システムの「可視化・分析層」を担うOpenObserveのKubernetesデプロイメント。

## 🎯 **概要**

OpenObserveは、ログ、メトリクス、トレースを統合的に管理・可視化する超軽量な可観測性プラットフォームです。
従来のリッチな構成（Grafana + Loki + Tempoなど）と比較して圧倒的に少ないリソースで動作し、Rust製による高速な処理が特徴です。

### **システムの役割**
*   **📈 データの可視化**: 電力消費やコストのダッシュボード表示（従来のGrafanaの役割を代替）
*   **🗄️ ログ管理**: マイクロサービス群（BFF, Exporter）からのログ集約
*   **🔗 統合バックエンド**: フロントエンドとしての役割と、データストアとしての役割を兼務

## 🤝 **他サービスとの接続**

*   **MinIO (S3互換ストレージ)**:
    *   OpenObserveのデータ永続化先として使用されます。
    *   ログやメトリクスの長期保存を行います。
*   **VictoriaMetrics**:
    *   データの相互運用や、PromQL互換のクエリインターフェースを通じて連携します。

## ⚙️ **環境変数・設定**

OpenObserveの動作に必要な環境変数は、Deployment定義およびKubernetesのSecretから注入されます。
機密情報は `k8s/.env` ファイルで管理し、`make k8s-secret-generate` コマンドでSecretを生成します。

### **認証・ユーザー設定**

| 環境変数名              | 説明                         | 注入元                                              |
| ----------------------- | ---------------------------- | --------------------------------------------------- |
| `ZO_ROOT_USER_EMAIL`    | rootユーザーのメールアドレス | Secret: `openobserve-credentials` (key: `email`)    |
| `ZO_ROOT_USER_PASSWORD` | rootユーザーのパスワード     | Secret: `openobserve-credentials` (key: `password`) |

### **ストレージ設定 (MinIO連携)**

OpenObserveはバックエンドストレージとしてMinIOを使用するため、MinIOの接続情報も環境変数として設定されます。

| 環境変数名                | 設定値（デフォルト） | 説明                                             |
| ------------------------- | -------------------- | ------------------------------------------------ |
| `ZO_S3_PROVIDER`          | `s3`                 | ストレージプロバイダ指定                         |
| `ZO_S3_SERVER_URL`        | `http://minio:9000`  | MinIOのエンドポイントURL                         |
| `ZO_S3_REGION_NAME`       | `us-east-1`          | S3リージョン名（MinIO互換用）                    |
| `ZO_S3_BUCKET_NAME`       | `openobserve`        | データを保存するバケット名                       |
| `ZO_S3_ACCESS_KEY_ID`     | (from Secret)        | MinIOアクセスキー（`minio-credentials`より）     |
| `ZO_S3_SECRET_ACCESS_KEY` | (from Secret)        | MinIOシークレットキー（`minio-credentials`より） |

### **システム設定**

| 環境変数名                 | 設定値 | 説明                                       |
| -------------------------- | ------ | ------------------------------------------ |
| `ZO_MEMORY_CACHE_MAX_SIZE` | `256`  | インメモリキャッシュの最大サイズ (MB)      |
| `ZO_NODE_ROLE`             | `all`  | ノードの役割（単一ノード構成のため `all`） |

### **設定ファイル (k8s/.env)**

デプロイ前に以下の変数を `k8s/.env` に設定する必要があります。

```bash
# OpenObserve
ZO_ROOT_USER_EMAIL=admin@example.com      # -> ZO_ROOT_USER_EMAIL
ZO_ROOT_USER_PASSWORD=ComplexPassword123! # -> ZO_ROOT_USER_PASSWORD
```

## 🚀 **デプロイメント & 動作確認**

OpenObserveは `overlays/production` の一部としてデプロイされることを想定しています（認証情報SecretがOverlay層で管理されているため）。
単体での適用ではなく、システム全体としてデプロイしてください。

### **デプロイ**

```bash
# 全体（Productoin環境）のデプロイ
make k8s-deploy-production

# または手動で実行:
# make k8s-secret-generate
# kubectl apply -k k8s/overlays/production
```

### **動作確認**

WEB UIへのアクセス：

```bash
# ポートフォワードの開始
kubectl port-forward -n smart-home svc/openobserve 5080:5080
```

ブラウザで `http://localhost:5080` にアクセスしてください。
※ 初回ログイン情報は Kubernetes の Secret (`openobserve-credentials`) で管理されています。
