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

| ファイル                         | 内容                                   |
| -------------------------------- | -------------------------------------- |
| `deployment.yaml`                | dummy-exporter コンテナのデプロイ設定  |
| `service.yaml`                   | ClusterIP サービス（ポート 9100）      |
| `configmap-initial-devices.yaml` | 起動時に一括登録される初期デバイス定義 |
| `kustomization.yaml`             | このコンポーネントのリソース一覧       |

---

## 初期デバイス

dummy-exporter は起動時に ConfigMap で定義したデバイスを自動登録する。
デバイスを追加・変更したい場合は `configmap-initial-devices.yaml` の JSON を編集し、
Pod を再起動すれば反映される。

現在登録されているデバイスは `work / living / kitchen / bedroom` の4部屋にまたがる計10台で、
Grafana ダッシュボードで複数部屋の消費電力を確認できる構成になっている。

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

### VictoriaMetrics でのスクレイプ確認

dummy-exporter が VictoriaMetrics に取り込まれているか確認:

```bash
kubectl port-forward -n smart-home svc/prod-victoriametrics 8428:8428

# dummy-exporter のメトリクスが存在するか
curl 'http://localhost:8428/api/v1/query?query=device_power_watts' | python3 -m json.tool
```

