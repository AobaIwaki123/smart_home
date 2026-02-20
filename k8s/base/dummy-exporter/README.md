# dummy-exporter - 開発用ダミーメトリクス生成器

## 役割

dummy-exporter は**開発・テスト環境でのみ使用するコンポーネント**で、  
SwitchBot API への接続なしに Prometheus 形式のダミーメトリクスを生成する。

- 実デバイスと同等の形式でメトリクスを `/metrics` に公開
- ランダムなジッターを加えることで実デバイスに近い変動を再現
- VictoriaMetrics がスクレイプするターゲットとして登録される

本番環境（`production` overlay）でも同様のデプロイが含まれており、  
Grafana ダッシュボードの動作確認に使用できる。

---

## 公開メトリクス（主要なもの）

| メトリクス名         | 種別  | 内容                                 |
| -------------------- | ----- | ------------------------------------ |
| `device_power_watts` | Gauge | デバイスの消費電力（W）              |
| `device_up`          | Gauge | デバイスの死活状態（1=正常, 0=異常） |

エンドポイント: `http://<service>:9100/metrics`  
ヘルスチェック: `http://<service>:9100/healthz`

---

## 構成ファイル

| ファイル             | 内容                                  |
| -------------------- | ------------------------------------- |
| `deployment.yaml`    | dummy-exporter コンテナのデプロイ設定 |
| `service.yaml`       | ClusterIP サービス（ポート 9100）     |
| `kustomization.yaml` | このコンポーネントのリソース一覧      |

イメージは `ghcr.io/aobaiwaki123/dummy-exporter:latest`。  
ソースコードは [`services/dummy-exporter/`](../../../../services/dummy-exporter/) にある。

---

## デプロイ

```bash
# 本番環境全体をデプロイ（dummy-exporter を含む）
make k8s-deploy-production

# 状態確認
kubectl get pods -n smart-home -l app=dummy-exporter
```

---

## 動作確認・デバッグ

### メトリクスの手動取得

```bash
kubectl port-forward -n smart-home svc/prod-dummy-exporter 9100:9100

# メトリクス確認
curl http://localhost:9100/metrics

# ヘルスチェック
curl http://localhost:9100/healthz
```

### ログ確認

```bash
kubectl logs -n smart-home deploy/prod-dummy-exporter -f
```

### VictoriaMetrics でのスクレイプ確認

dummy-exporter が VictoriaMetrics に取り込まれているか確認:

```bash
kubectl port-forward -n smart-home svc/prod-victoriametrics 8428:8428

# dummy-exporter のメトリクスが存在するか
curl 'http://localhost:8428/api/v1/query?query=device_power_watts' | python3 -m json.tool
```

---

## ローカル（Docker）での動作確認

```bash
# Docker イメージビルド
make docker-build-dummy

# コンテナ起動（ポート 9100 で公開）
make docker-run-dummy

# ログ監視
make docker-logs-dummy

# 停止
make docker-down-dummy
```
