# VictoriaMetrics - 時系列データベース

スマートホーム監視システムの「記憶層」を担うVictoriaMetricsのKubernetesデプロイメント。

## 🎯 **概要**

VictoriaMetricsは、SwitchBot Exporterから収集される電力データを時系列で保存・管理する軽量な時系列データベースです。Prometheusと完全互換でありながら、リソース効率が高く、自宅インフラに最適化されています。

### **主な特徴**
- 📊 **Prometheus互換**: PromQLクエリがそのまま使用可能
- 🚀 **軽量設計**: メモリ使用量がPrometheusの約半分
- 💾 **高圧縮率**: ディスク使用量を大幅に削減
- 🔄 **長期保存**: 12ヶ月のデータ保持（設定変更可能）

## 📁 **構成ファイル**

| ファイル                                                   | 役割                 | 説明                                    |
| ---------------------------------------------------------- | -------------------- | --------------------------------------- |
| [`statefulset.yaml`](statefulset.yaml)                     | **データベース本体** | VictoriaMetricsコンテナとストレージ設定 |
| [`service.yaml`](service.yaml)                             | **ネットワーク露出** | BFF・Grafana等からのアクセス窓口        |
| [`configmap.yaml`](configmap.yaml)                         | **収集設定**         | Exporterからのデータ自動収集ルール      |
| [`persistentvolumeclaim.yaml`](persistentvolumeclaim.yaml) | **永続化ストレージ** | データの永続保存領域（20GB）            |

## 🚀 **デプロイメント**

### **事前準備**
Exporterが稼働していることを確認してください：
```bash
kubectl get pods -n smart-home -l app=switchbot-exporter
```

### **デプロイ実行**
```bash
# VictoriaMetricsのみデプロイ
kubectl apply -k k8s/base/victoria-metrics/

# ベース全体（Exporter + VictoriaMetrics）をデプロイ
kubectl apply -k k8s/base/
```

### **デプロイ確認**
```bash
# Pod状態確認
kubectl get pods -n smart-home -l app=victoria-metrics

# ストレージ確認
kubectl get pvc -n smart-home

# サービス確認
kubectl get svc -n smart-home -l app=victoria-metrics
```

## 📈 **動作確認・モニタリング**

### **1. データ収集状況の確認**
```bash
# VictoriaMetricsの管理画面にアクセス
kubectl port-forward -n smart-home svc/victoria-metrics 8428:8428

# ブラウザで以下にアクセス:
# http://localhost:8428 (管理画面)
# http://localhost:8428/targets (収集対象の状況)
```

### **2. メトリクスクエリの実行**
VictoriaMetrics管理画面または `curl` でクエリを実行：

```bash
# 接続テスト
curl "http://localhost:8428/api/v1/query?query=up"

# 電力データの確認
curl "http://localhost:8428/api/v1/query?query=smart_home_power_watts"

# デバイス別電力の時系列取得
curl "http://localhost:8428/api/v1/query_range?query=smart_home_power_watts&start=2026-02-19T00:00:00Z&end=2026-02-19T23:59:59Z&step=300s"
```

### **3. データ保存量の監視**
```bash
# ストレージ使用量確認
kubectl exec -n smart-home victoria-metrics-0 -- df -h /victoria-metrics-data

# VictoriaMetrics内部メトリクス確認
curl "http://localhost:8428/metrics" | grep vm_
```

## ⚙️ **設定のカスタマイズ**

### **収集間隔の調整**
[`configmap.yaml`](configmap.yaml) の `scrape_interval` を変更：
```yaml
global:
  scrape_interval: 30s  # 15s, 60s等に変更可能
```

### **データ保持期間の変更**
[`statefulset.yaml`](statefulset.yaml) の `retentionPeriod` を調整：
```yaml
args:
  - -retentionPeriod=6m   # 6ヶ月に短縮
  - -retentionPeriod=24m  # 2年に延長
```

### **ストレージ容量の拡張**
[`persistentvolumeclaim.yaml`](persistentvolumeclaim.yaml) の容量を変更：
```yaml
spec:
  resources:
    requests:
      storage: 50Gi  # 20Giから50Giに拡張
```

## 🔧 **トラブルシューティング**

### **Pod起動失敗**
```bash
# Pod状態詳細確認
kubectl describe pod -n smart-home victoria-metrics-0

# イベント確認
kubectl get events -n smart-home --field-selector involvedObject.name=victoria-metrics-0

# ログ確認
kubectl logs -n smart-home victoria-metrics-0
```

### **データ収集エラー**
```bash
# Exporter接続状況確認
kubectl exec -n smart-home victoria-metrics-0 -- curl -f http://exporter.smart-home.svc.cluster.local:8000/metrics

# 設定確認
kubectl exec -n smart-home victoria-metrics-0 -- cat /etc/prometheus/prometheus.yml
```

### **ストレージ問題**
```bash
# PVC状態確認
kubectl describe pvc -n smart-home victoria-metrics-storage

# ノードのストレージ容量確認
kubectl get nodes -o wide
kubectl describe nodes
```

### **高負荷時の対応**
```bash
# リソース使用量確認
kubectl top pod -n smart-home victoria-metrics-0

# メモリ制限値の調整
kubectl patch statefulset victoria-metrics -n smart-home --patch='
spec:
  template:
    spec:
      containers:
      - name: victoria-metrics
        resources:
          limits:
            memory: "4Gi"  # 2Giから4Giに増加
'
```

## 📊 **次のステップ**

VictoriaMetricsが稼働したら、以下の拡張が可能になります：

1. **[📈 Grafanaダッシュボード](../grafana/README.md)** - 美しい可視化
2. **[⚡ BFF API](../../services/bff/README.md)** - コスト計算ロジック  
3. **[🔔 アラート](../alertmanager/README.md)** - 異常検知と通知

## 💡 **パフォーマンス最適化Tips**

### **インデックス効率化**
```bash
# カーディナリティ確認（ラベル種類数）
curl "http://localhost:8428/api/v1/label/__name__/values" | jq '.'

# 高カーディナリティラベルの特定
curl "http://localhost:8428/api/v1/labels" | jq '.'
```

### **クエリ最適化**
```bash
# 重いクエリの特定
curl "http://localhost:8428/api/v1/status/top_queries"

# クエリ実行時間の確認
curl "http://localhost:8428/api/v1/query?query=smart_home_power_watts&time=$(date +%s)"
```