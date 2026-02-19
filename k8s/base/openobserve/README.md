# OpenObserve - 可観測性プラットフォーム

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

## 🚀 **デプロイメント & 動作確認**

### **デプロイ**

```bash
# OpenObserveを含むベース環境の適用
kubectl apply -k k8s/base/openobserve
```

### **動作確認**

WEB UIへのアクセス：

```bash
# ポートフォワードの開始
kubectl port-forward -n smart-home svc/openobserve 5080:5080
```

ブラウザで `http://localhost:5080` にアクセスしてください。
※ 初回ログイン情報は Kubernetes の Secret (`openobserve-credentials`) で管理されています。
