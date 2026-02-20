# SwitchBot Exporter - Prometheus メトリクスエクスポーター

SwitchBot APIから電力データを取得し、Prometheus形式で公開するKubernetesデプロイメント。

## 🎯 **概要**

SwitchBot Exporterは、SwitchBot Hub Plus/Meterデバイスから電力・環境データを収集し、VictoriaMetricsが読み取れる形式で公開する「データ収集エンジン」です。

### **主な機能**
- 🔌 **電力監視**: Plug Mini (JP)の消費電力を監視
- 📡 **API連携**: SwitchBot Web APIと安全に通信
- 📊 **Prometheusメトリクス**: `/metrics`エンドポイントでデータ公開
- 🧪 **モック機能**: 開発・テスト用のダミーデータ生成

## 📁 **構成ファイル**

| ファイル                             | 役割                     | 説明                              |
| ------------------------------------ | ------------------------ | --------------------------------- |
| [`deployment.yaml`](deployment.yaml) | **アプリケーション実行** | Exporterコンテナのデプロイ設定    |
| [`service.yaml`](service.yaml)       | **ネットワーク露出**     | VictoriaMetricsからのアクセス窓口 |
| [`configmap.yaml`](configmap.yaml)   | **デバイス設定**         | 監視対象デバイスの一覧と設定      |

## 🚀 **デプロイメント方法**

### **本番環境（実際のAPIキー使用）**
実際のSwitchBotデバイスからデータ収集：

#### **1. 事前準備**
```bash
# プロジェクトルートで実行
cp k8s/.env.example k8s/.env
# k8s/.env を編集して実際のAPIキーを設定

# Makefileでsecret.yaml生成
make k8s-secret-generate
```

#### **2. デプロイ実行**
```bash
# 本番環境デプロイ
kubectl apply -k k8s/overlays/production/

# 動作確認
kubectl get pods -n smart-home -l app=switchbot-exporter
kubectl logs -n smart-home -l app=switchbot-exporter -f
```

## 📊 **公開メトリクス**

### **電力系メトリクス**
| メトリクス名                  | 型      | 説明                              | ラベル                             |
| ----------------------------- | ------- | --------------------------------- | ---------------------------------- |
| `smart_home_power_watts`      | Gauge   | 瞬間消費電力 (W)                  | `device_id`, `device_name`, `room` |
| `smart_home_energy_kwh_total` | Counter | 累積電力量 (kWh)                  | `device_id`, `device_name`, `room` |
| `smart_home_device_up`        | Gauge   | デバイス接続状態 (1=接続, 0=切断) | `device_id`, `device_name`         |

### **システム系メトリクス**
| メトリクス名                         | 型        | 説明            |
| ------------------------------------ | --------- | --------------- |
| `smart_home_api_requests_total`      | Counter   | API呼び出し回数 |
| `smart_home_api_errors_total`        | Counter   | APIエラー回数   |
| `smart_home_scrape_duration_seconds` | Histogram | データ収集時間  |

## ⚙️ **設定のカスタマイズ**

### **デバイス追加**
新しいSwitchBotデバイスを監視対象に追加：

[`configmap.yaml`](configmap.yaml) の `devices.json` を編集：
```json
{
  "devices": [
    {
      "deviceId": "新しいデバイスID",
      "deviceName": "新しいデバイス名",
      "deviceType": "Plug Mini (JP)",
      "room": "追加したい部屋名"
    }
  ]
}
```

### **収集間隔の調整**
[`deployment.yaml`](deployment.yaml) の環境変数を変更：
```yaml
env:
- name: SCRAPE_INTERVAL
  value: "30"  # 30秒間隔（デフォルト: 15秒）
```

### **リソース制限の変更**
```yaml
resources:
  limits:
    cpu: "200m"     # 100m -> 200m に増加
    memory: "256Mi"  # 128Mi -> 256Mi に増加
  requests:
    cpu: "50m"
    memory: "64Mi"
```

## 🔧 **トラブルシューティング**

### **API認証エラー**
```bash
# Secret確認
kubectl get secret switchbot-credentials -n smart-home -o yaml

# 環境変数確認
kubectl exec -n smart-home $(kubectl get pod -n smart-home -l app=switchbot-exporter -o jsonpath="{.items[0].metadata.name}") -- env | grep SWITCHBOT

# ログでエラー詳細確認
kubectl logs -n smart-home -l app=switchbot-exporter --tail=50
```

### **デバイス接続エラー**
```bash
# メトリクス確認
kubectl port-forward -n smart-home svc/exporter 8000:8000
curl "http://localhost:8000/metrics" | grep smart_home_device_up

# ConfigMap内容確認
kubectl get configmap devices-config -n smart-home -o yaml

# デバイス情報の再収集
kubectl rollout restart deployment/prod-switchbot-exporter -n smart-home
```

### **メトリクス公開エラー**
```bash
# エンドポイント疎通確認
kubectl exec -n smart-home $(kubectl get pod -n smart-home -l app=switchbot-exporter -o jsonpath="{.items[0].metadata.name}") -- curl -f http://localhost:8000/metrics

# サービス確認
kubectl get endpoints exporter -n smart-home

# NetworkPolicy確認（ある場合）
kubectl get networkpolicy -n smart-home
```

### **高負荷時の対応**
```bash
# リソース使用量監視
kubectl top pod -n smart-home -l app=switchbot-exporter

# API呼び出し頻度確認
kubectl logs -n smart-home -l app=switchbot-exporter | grep "API call"

# レート制限対応
# deployment.yamlでSCRAPE_INTERVALを増加（15s -> 30s等）
```

## 🔍 **ログ解析**

### **正常動作ログの例**
```
2026-02-19T12:00:00Z INFO Starting SwitchBot Exporter
2026-02-19T12:00:01Z INFO Loaded 5 devices from config
2026-02-19T12:00:02Z INFO Started HTTP server on :8000
2026-02-19T12:00:15Z INFO Scraping device: living-room-tv (deviceId: ABC123)
2026-02-19T12:00:15Z INFO Device living-room-tv: 45.2W
```

### **エラーログのパターン**
```bash
# API認証エラー
"ERROR: Authentication failed: invalid token"

# デバイス接続エラー  
"ERROR: Device ABC123 not responding"

# レート制限エラー
"ERROR: API rate limit exceeded, retrying in 60s"
```

## 📈 **パフォーマンス監視**

### **メトリクス監視コマンド**
```bash
# VictoriaMetricsとの連携確認
kubectl exec -n smart-home victoria-metrics-0 -- curl -s "http://exporter.smart-home.svc.cluster.local:8000/metrics" | head -20

# 収集データ量の確認
curl "http://localhost:8428/api/v1/query?query=smart_home_power_watts" | jq '.data.result | length'

# API呼び出し頻度確認
curl "http://localhost:8428/api/v1/query?query=rate(smart_home_api_requests_total[5m])"
```

## 🔗 **関連コンポーネント**

### **データフロー**
```
[SwitchBot API] 
      ↓
[🔌 Exporter] ← devices.json (ConfigMap)
      ↓ :8000/metrics
[📊 VictoriaMetrics] 
      ↓ PromQL
[📈 Grafana Dashboard]
```

### **次のステップ**
1. **[📊 VictoriaMetrics](../victoria-metrics/README.md)** でデータを永続化
2. **[⚡ BFF API](../../services/bff/README.md)** でコスト計算
3. **[📱 Frontend](../../services/frontend/README.md)** で可視化