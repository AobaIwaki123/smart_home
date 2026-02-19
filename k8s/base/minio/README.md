# MinIO - S3互換オブジェクトストレージ

スマートホーム監視システムの「データ永続化層」を支えるMinIOのKubernetesデプロイメント。

## 🎯 **概要**

MinIOは、Amazon S3互換のAPIを提供する高性能なオブジェクトストレージです。
Kubernetesクラスタ内で動作し、ステートフルなアプリケーションに対して信頼性の高いストレージバックエンドを提供します。

### **システムの役割**
*   **📦 データ保存**: OpenObserveなどのアプリケーションが生成するログやインデックスデータの保存先として機能します。
*   **💾 永続化**: Podの再起動や再作成が行われても、重要なデータが失われないように永続ボリューム（PVC）上にデータを保持します。

## 🤝 **他サービスとの接続**

*   **OpenObserve**:
    *   OpenObserveのプライマリストレージとして構成されています。
    *   OpenObserveは内部的にS3 APIを使用して、MinIOに対してデータの読み書きを行います。

## ⚙️ **環境変数・設定**

MinIOの動作に必要な環境変数は、KubernetesのSecretおよびConfigMapを通じて注入されます。
機密情報は `k8s/.env` ファイルで管理し、`make k8s-secret-generate` コマンドでSecretを生成します。

| 環境変数名            | 説明                                 | 注入元                                          |
| --------------------- | ------------------------------------ | ----------------------------------------------- |
| `MINIO_ROOT_USER`     | 管理者ユーザー名（アクセスキー）     | Secret: `minio-credentials` (key: `access-key`) |
| `MINIO_ROOT_PASSWORD` | 管理者パスワード（シークレットキー） | Secret: `minio-credentials` (key: `secret-key`) |

### **設定ファイル (k8s/.env)**

デプロイ前に以下の変数を `k8s/.env` に設定する必要があります。

```bash
# MinIO (S3 Compatible Storage)
MINIO_ACCESS_KEY=your-minio-access-key  # -> MINIO_ROOT_USER
MINIO_SECRET_KEY=your-minio-secret-key  # -> MINIO_ROOT_PASSWORD
```

## 🚀 **デプロイメント & 動作確認**

MinIOは `overlays/production` の一部としてデプロイされることを想定しています（認証情報SecretがOverlay層で管理されているため）。
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

MinIO Console（管理画面）へのアクセス：

```bash
# ポートフォワードの開始
kubectl port-forward -n smart-home svc/minio 9001:9001
```

ブラウザで `http://localhost:9001` にアクセスしてください。
※ ログイン情報は Kubernetes の Secret (`minio-credentials`) で管理されています。
