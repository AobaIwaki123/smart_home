# VictoriaMetrics - 時系列データベース

## 役割

VictoriaMetrics は本システムの**時系列メトリクスストレージ兼スクレイプエンジン**として動作する。

- Exporter / dummy-exporter が公開する `/metrics` エンドポイントを定期的にスクレイプ
- 取得したデータを Pod 内の PersistentVolume に保存（デフォルト保存期間: 12 ヶ月）
- PromQL 互換の HTTP API を提供し、Grafana のデータソースとして機能する

外部の vmagent や Prometheus は使用せず、VictoriaMetrics 単体でスクレイプからクエリまでを完結させるシンプルな構成。

---

## 構成ファイル

| ファイル             | 内容                                   |
| -------------------- | -------------------------------------- |
| `deployment.yaml`    | VictoriaMetrics コンテナのデプロイ設定 |
| `service.yaml`       | ClusterIP サービス（ポート 8428）      |
| `configmap.yaml`     | スクレイプ設定（`scrape.yml`）         |
| `pvc.yaml`           | データ永続化用 PersistentVolumeClaim   |
| `kustomization.yaml` | このコンポーネントのリソース一覧       |

スクレイプ対象は `configmap.yaml` の `scrape_configs` で定義される。  
本番環境では `k8s/overlays/production/victoriametrics-config-patch.yaml` で上書きされる。

---

## デプロイ

```bash
# 本番環境全体をデプロイ（secret 生成込み）
make k8s-deploy-production

# 状態確認
kubectl get pods -n smart-home -l app=victoriametrics
kubectl get pvc  -n smart-home
```

---

## 動作確認・デバッグ

### UI へのアクセス

```bash
kubectl port-forward -n smart-home svc/prod-victoriametrics 8428:8428
```

ブラウザで http://localhost:8428 を開くと VictoriaMetrics の組み込み UI が使える。

主なエンドポイント:

| パス                     | 用途                             |
| ------------------------ | -------------------------------- |
| `/`                      | 組み込み UI（PromQL クエリ実行） |
| `/api/v1/query?query=up` | PromQL API（Grafana が利用）     |
| `/metrics`               | VictoriaMetrics 自身のメトリクス |
| `/health`                | ヘルスチェック                   |
| `/targets`               | スクレイプ対象の状態一覧         |

### スクレイプ状態の確認

```bash
# /targets で各ジョブが "up" になっているか確認
curl http://localhost:8428/targets | python3 -m json.tool | grep -E '"health"|"job"'
```

### ログ確認

```bash
kubectl logs -n smart-home deploy/prod-victoriametrics -f
kubectl logs -n smart-home deploy/prod-victoriametrics --previous   # 再起動後の前回ログ
```

### PVC の使用量確認

```bash
kubectl exec -n smart-home deploy/prod-victoriametrics -- df -h /victoria-metrics-data
```

---

## 注意事項

- `strategy.type: Recreate` のため、デプロイ時に一時的なダウンタイムが発生する
- PVC を削除するとすべてのメトリクス履歴が失われる
- スクレイプ設定を変更した場合は Pod の再起動が必要（ConfigMap は自動リロードしない）
