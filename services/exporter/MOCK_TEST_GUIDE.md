# SwitchBot Exporter - モックデータ動作確認手順

このガイドは、実際の SwitchBot API を使わずに、モックデータでエクスポーターの動作確認を行う手順を説明します。

## 🎯 概要

SwitchBot Exporter には以下のモック機能が実装されています：

- **モック API レスポンス**: `weight`フィールドを含むリアルな API レスポンス形式
- **動的電力値**: 80%の確率で待機電力（5-10W）、20%の確率で高負荷（100-300W）をシミュレート
- **可視化対応**: VictoriaMetrics/Grafana での興味深いグラフ生成が可能

## 🚀 モックデータでの動作確認

### STEP 1: 環境変数の設定

```bash
# モックモードを有効化
export USE_MOCK=true

# その他の設定（オプション）
export LOG_LEVEL=DEBUG
export COLLECTION_INTERVAL=10  # 10秒間隔で高頻度テスト
export METRICS_PORT=8000
```

### STEP 2: デバイス設定の確認

`devices.json` ファイルが作成されていることを確認してください：

```bash
cat devices.json
```

期待される出力：
```json
[
  {
    "id": "V2E012345678",
    "name": "server", 
    "house": "myhome",
    "room": "work",
    "shelf": "rack_1"
  },
  ...
]
```

### STEP 3: Docker Compose でのモック実行

```bash
# モックモードでエクスポーターを起動
USE_MOCK=true docker compose up switchbot-exporter

# または バックグラウンドで実行
USE_MOCK=true docker compose up -d switchbot-exporter
```

### STEP 4: メトリクス確認

新しいターミナルを開いて以下を実行：

```bash
# メトリクスエンドポイントにアクセス
curl http://localhost:8000/metrics

# または ブラウザで確認
open http://localhost:8000/metrics
```

## ✅ 期待される出力形式

### 1. 正常なメトリクス出力例

```text
# HELP switchbot_power_watts Current power usage in Watts
# TYPE switchbot_power_watts gauge
switchbot_power_watts{device_id="V2E012345678",device_name="server",house="myhome",room="work",shelf="rack_1"} 12.5
switchbot_power_watts{device_id="V2E987654321",device_name="nas",house="myhome",room="work",shelf="rack_2"} 156.7
switchbot_power_watts{device_id="V2E555666777",device_name="router",house="myhome",room="living",shelf="tv_board"} 8.3

# HELP switchbot_device_up Device availability (1: OK, 0: NG)
# TYPE switchbot_device_up gauge
switchbot_device_up{device_id="V2E012345678"} 1
switchbot_device_up{device_id="V2E987654321"} 1
switchbot_device_up{device_id="V2E555666777"} 1

# HELP switchbot_api_requests_remaining Remaining API calls for the day
# TYPE switchbot_api_requests_remaining gauge
switchbot_api_requests_remaining 9999
```

### 2. ログ出力例

```text
2026-02-19 10:30:45,123 - INFO - Loaded 3 devices from config
2026-02-19 10:30:45,124 - INFO - Prometheus metrics server started on port 8000
2026-02-19 10:30:45,125 - WARNING - ⚠️ MOCK MODE ENABLED - Not using real SwitchBot API
2026-02-19 10:30:45,126 - INFO - Using MOCK mode for data collection
2026-02-19 10:30:45,127 - INFO - Mock data updated: V2E012345678 = 12.5W
2026-02-19 10:30:45,128 - INFO - Mock data updated: V2E987654321 = 156.7W
2026-02-19 10:30:45,129 - INFO - Mock data updated: V2E555666777 = 8.3W
2026-02-19 10:30:45,130 - INFO - Metrics collection completed. Next run in 10s
```

## 🧪 動作確認チェックリスト

- [ ] **フィールドマッピング**: `weight` の値が `switchbot_power_watts` に正しく反映されている
- [ ] **ラベル注入**: 設定ファイルの `house`, `room`, `shelf` がラベルとして付与されている
- [ ] **動的値**: 複数回アクセスして電力値が変動している（待機電力 ↔ 高負荷）
- [ ] **API制限表示**: `switchbot_api_requests_remaining` が 9999 に設定されている
- [ ] **デバイス可用性**: 全ての `switchbot_device_up` が 1 になっている

## 🔧 トラブルシューティング

### メトリクスが表示されない場合

1. **ポート確認**:
   ```bash
   netstat -an | grep 8000
   # または
   lsof -i :8000
   ```

2. **コンテナログの確認**:
   ```bash
   docker compose logs switchbot-exporter
   ```

3. **環境変数の確認**:
   ```bash
   docker compose exec switchbot-exporter env | grep USE_MOCK
   ```

### 設定ファイルが読み込まれない場合

```bash
# コンテナ内のファイル存在確認
docker compose exec switchbot-exporter ls -la /app/devices.json
```

## ⚡ 高頻度テストモード 

開発時により頻繁な動作確認をしたい場合：

```bash
# 5秒間隔で収集
USE_MOCK=true COLLECTION_INTERVAL=5 LOG_LEVEL=DEBUG docker compose up switchbot-exporter
```

## 🎨 可視化テスト（オプション）

Prometheus も同時起動して可視化をテストする場合：

```bash
# エクスポーター + Prometheus を同時起動
USE_MOCK=true docker compose --profile prometheus up

# Prometheus UI を確認
open http://localhost:9090
```

PrometheusのUIで `switchbot_power_watts` クエリを実行すると、モックデータによる動的な電力値の変化をグラフで確認できます。

## 🚦 実際のAPIモードへの切り替え

モックテストが完了したら、以下で実際のAPIモードに切り替えます：

```bash
# 1. モックモードを無効化
export USE_MOCK=false

# 2. 実際のAPI認証情報を設定
export SWITCHBOT_TOKEN="your_actual_token"
export SWITCHBOT_SECRET="your_actual_secret"

# 3. 再起動
docker compose restart switchbot-exporter
```

これで本番環境と同等の動作確認が可能です！