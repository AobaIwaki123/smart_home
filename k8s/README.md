# SwitchBot Exporter - Kubernetes デプロイメントガイド

このディレクトリには、SwitchBot ExporterをKubernetesクラスター上の **`smart-home`ネームスペース** にデプロイするためのマニフェストファイルが格納されています。

## 構成一覧

```
k8s/
├── base/                       # 共通の基本設定
│   ├── kustomization.yaml      # プロジェクト全体のベース設定
│   ├── namespace.yaml          # smart-homeネームスペース定義
│   └── exporter/               # SwitchBot Exporter固有のリソース
│       ├── kustomization.yaml  # Exporterベース設定
│       ├── deployment.yaml     # Deployment定義
│       ├── service.yaml        # Service定義
│       └── configmap.yaml      # デバイス設定（devices.json）
└── overlays/
    ├── mock/                   # モック環境用設定
    │   ├── kustomization.yaml
    │   └── deployment-patch.yaml
    └── production/             # 本番環境用設定
        ├── kustomization.yaml
        ├── secret.yaml
        └── deployment-patch.yaml
```

## Namespace戦略

このプロジェクトでは **`smart-home`** ネームスペースを使用してリソースを隔離・管理します。

### メリット
- **名前衝突の回避**: 他のプロジェクトとの干渉を防止
- **権限・リソース管理**: ResourceQuotaでプロジェクト単位の制限設定が可能
- **一括削除**: `kubectl delete ns smart-home` でプロジェクト関連リソースを完全削除

## 主な変更点（DockerからKubernetesへ）

| 項目               | Docker Compose      | Kubernetes          |
| ------------------ | ------------------- | ------------------- |
| **デバイス設定**   | `COPY devices.json` | ConfigMapでマウント |
| **API認証情報**    | 環境変数            | Secretリソース      |
| **モック切り替え** | `USE_MOCK` env var  | Overlay設定         |
| **設定管理**       | `.env` ファイル     | Kustomize           |

## デプロイ手順

### 1. モック環境のデプロイ

開発・テスト用のモック環境をデプロイします（SwitchBot APIは使用しません）。

```bash
# smart-homeネームスペースが自動的に作成されます
kubectl apply -k k8s/overlays/mock

# デプロイ確認（ネームスペースを指定）
kubectl get pods -n smart-home -l app=switchbot-exporter

# ログ確認
kubectl logs -n smart-home -l app=switchbot-exporter -f

# メトリクス確認
kubectl port-forward -n smart-home svc/mock-switchbot-exporter 8000:8000
# ブラウザで http://localhost:8000/metrics にアクセス
```

### 2. 本番環境のデプロイ

実際のSwitchBot APIを使用する本番環境をデプロイします。

#### 事前準備：認証情報の設定

```bash
# 実際のSwitchBot API認証情報をsmart-homeネームスペースに設定
kubectl create secret generic switchbot-credentials \
  --from-literal=token="YOUR_ACTUAL_SWITCHBOT_TOKEN" \
  --from-literal=secret="YOUR_ACTUAL_SWITCHBOT_SECRET" \
  --namespace=smart-home

# または、secretファイルを事前に編集してから適用
# vi k8s/overlays/production/secret.yaml
# kubectl apply -f k8s/overlays/production/secret.yaml
```

#### デプロイ

```bash
# 本番環境のデプロイ
kubectl apply -k k8s/overlays/production

# デプロイ確認
kubectl get pods -n smart-home -l app=switchbot-exporter

# Secret が正しく作成されているか確認
kubectl get secret switchbot-credentials -n smart-home -o yaml

# ログ確認（実際のAPIを叩いています）
kubectl logs -n smart-home -l app=switchbot-exporter -f
```

### 3. メトリクス収集の確認

```bash
# Pod内部からメトリクスエンドポイントを確認
kubectl exec -it -n smart-home $(kubectl get pod -n smart-home -l app=switchbot-exporter -o jsonpath="{.items[0].metadata.name}") -- curl http://localhost:8000/metrics

# 外部からアクセス（ポートフォワード）
kubectl port-forward -n smart-home svc/prod-switchbot-exporter 8000:8000
```

## カスタマイズ

### デバイス設定の更新

新しいSwitchBotデバイスを追加する場合：

1. [k8s/base/exporter/configmap.yaml](k8s/base/exporter/configmap.yaml) の `devices.json` を編集
2. ConfigMapを再適用: `kubectl apply -k k8s/overlays/production`
3. Podを再起動: `kubectl rollout restart deployment/prod-switchbot-exporter -n smart-home`

### イメージの更新

新しいバージョンをデプロイする場合：

1. [k8s/overlays/production/kustomization.yaml](k8s/overlays/production/kustomization.yaml) の `newTag` を更新
2. 再適用: `kubectl apply -k k8s/overlays/production`

## セキュリティ注意事項

- **secret.yaml には実際の認証情報をコミットしないでください**
- 本番環境では必ず `kubectl create secret` コマンドを使用して認証情報を設定してください
- ConfigMapの内容は暗号化されていないため、機密情報は含めないでください

## トラブルシューティング

### Pod起動時のエラー

```bash
# Pod状態の確認
kubectl describe pod -n smart-home $(kubectl get pod -n smart-home -l app=switchbot-exporter -o jsonpath="{.items[0].metadata.name}")

# イベント確認
kubectl get events -n smart-home --sort-by='.metadata.creationTimestamp'

# ネームスペース全体のリソース確認
kubectl get all -n smart-home
```

### メトリクス取得エラー

```bash
# ヘルスチェック確認
kubectl exec -it -n smart-home $(kubectl get pod -n smart-home -l app=switchbot-exporter -o jsonpath="{.items[0].metadata.name}") -- curl -f http://localhost:8000/metrics

# ネットワーク確認
kubectl get svc -n smart-home -l app=switchbot-exporter
```

### リソース使用量の監視

```bash
# CPU/メモリ使用量確認
kubectl top pod -n smart-home -l app=switchbot-exporter

# リソース制限の確認
kubectl describe pod -n smart-home $(kubectl get pod -n smart-home -l app=switchbot-exporter -o jsonpath="{.items[0].metadata.name}") | grep -A 5 "Limits\|Requests"
```

### Namespace関連の管理コマンド

```bash
# smart-homeネームスペースの全リソース確認
kubectl get all -n smart-home

# Namespace削除（プロジェクト全体のクリーンアップ）
kubectl delete namespace smart-home

# ネームスペースの詳細確認
kubectl describe namespace smart-home
```