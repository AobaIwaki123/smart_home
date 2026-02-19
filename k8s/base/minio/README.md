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

## 🚀 **デプロイメント & 動作確認**

### **デプロイ**

```bash
# MinIOを含むベース環境の適用
kubectl apply -k k8s/base/minio
```

### **動作確認**

MinIO Console（管理画面）へのアクセス：

```bash
# ポートフォワードの開始
kubectl port-forward -n smart-home svc/minio 9001:9001
```

ブラウザで `http://localhost:9001` にアクセスしてください。
※ ログイン情報は Kubernetes の Secret (`minio-credentials`) で管理されています。
