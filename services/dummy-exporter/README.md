# dummy-exporter

Grafana テスト用の擬似データ生成 Prometheus Exporter。

本番 exporter と同一のメトリクス名 (`switchbot_power_watts`, `switchbot_device_up`) を返すため、
**既存の Grafana ダッシュボードをそのまま使って動作確認できる**。

## 起動方法

```bash
cd services/dummy-exporter
pip install -r requirements.txt
METRICS_PORT=9100 python -m uvicorn src.main:app --host 0.0.0.0 --port 9100
```

## 環境変数

| 変数                   | デフォルト             | 説明                                     |
| ---------------------- | ---------------------- | ---------------------------------------- |
| `METRICS_PORT`         | `9100`                 | HTTP ポート番号                          |
| `JITTER_INTERVAL`      | `15`                   | 自動ランダム変動の周期（秒）             |
| `LOG_LEVEL`            | `INFO`                 | ログレベル                               |
| `INITIAL_DEVICES_FILE` | `/config/devices.json` | 起動時に読み込む初期デバイス定義ファイル |

### 初期デバイスの登録

`INITIAL_DEVICES_FILE` に JSON ファイルのパスを指定すると、起動時にデバイスが自動登録される。
ファイルが存在しない場合はスキップされ、デバイスなしの状態で起動する。

k8s 環境では `configmap-initial-devices.yaml` をマウントすることで初期デバイスを注入している。
ローカル開発時は任意の JSON ファイルを用意して環境変数で指定できる。

---

## API リファレンス

### `GET /metrics`
Prometheus フォーマットでメトリクスを返す。

```bash
curl http://localhost:9100/metrics
```

### `GET /devices`
登録済みデバイスの一覧を返す。

```bash
curl http://localhost:9100/devices
```

---

### `POST /devices` — デバイス追加

```bash
curl -X POST http://localhost:9100/devices \
  -H 'Content-Type: application/json' \
  -d '{
    "device_id": "DUMMY001",
    "attrs": {
      "name": "pc_main",
      "room": "work",
      "shelf": "desk",
      "device": "pc",
      "parent_id": "none",
      "custom_tag": "any-value"
    },
    "power_watts": 120.0,
    "auto_jitter": true,
    "jitter_min": 80.0,
    "jitter_max": 250.0
  }'
```

| フィールド    | 型     | 必須 | 説明                                                                              |
| ------------- | ------ | ---- | --------------------------------------------------------------------------------- |
| `device_id`   | string | ✅    | 一意のデバイスID（k8s の監視対象 ID と合わせる）                                  |
| `attrs`       | object |      | 任意のキーバリュー。`name/room/shelf/device/parent_id` は Prometheus ラベルに使用 |
| `power_watts` | float  |      | 初期電力値（W）。デフォルト `10.0`                                                |
| `auto_jitter` | bool   |      | 自動ランダム変動。デフォルト `true`                                               |
| `jitter_min`  | float  |      | ジッター最小値（W）。デフォルト `5.0`                                             |
| `jitter_max`  | float  |      | ジッター最大値（W）。デフォルト `100.0`                                           |

---

### `DELETE /devices/{device_id}` — デバイス削除

```bash
curl -X DELETE http://localhost:9100/devices/DUMMY001
```

---

### `PUT /devices/{device_id}/power` — 電力値設定

```bash
# 250W に固定してジッターを止める
curl -X PUT http://localhost:9100/devices/DUMMY001/power \
  -H 'Content-Type: application/json' \
  -d '{"watts": 250.0, "auto_jitter": false}'

# ジッターはそのままで電力値だけ変える
curl -X PUT http://localhost:9100/devices/DUMMY001/power \
  -H 'Content-Type: application/json' \
  -d '{"watts": 50.0}'
```

| フィールド    | 型    | 必須 | 説明                                 |
| ------------- | ----- | ---- | ------------------------------------ |
| `watts`       | float | ✅    | 設定する電力値（W）                  |
| `auto_jitter` | bool  |      | 指定した場合のみ変更。省略で変更なし |

---

### `PUT /devices/{device_id}/state` — UP/DOWN 設定

```bash
# デバイスを DOWN にする（DEVICE_UP=0、電力=0 になる）
curl -X PUT http://localhost:9100/devices/DUMMY001/state \
  -H 'Content-Type: application/json' \
  -d '{"up": false}'

# デバイスを UP に戻す
curl -X PUT http://localhost:9100/devices/DUMMY001/state \
  -H 'Content-Type: application/json' \
  -d '{"up": true}'
```

---

### `PATCH /devices/{device_id}/attrs` — 属性情報の編集

既存の属性を部分更新する。対象の属性キーのみ上書きされる。
Prometheus ラベル (`room/shelf/device/name/parent_id`) を変更した場合、旧ラベルのメトリクスは自動削除される。

```bash
curl -X PATCH http://localhost:9100/devices/DUMMY001/attrs \
  -H 'Content-Type: application/json' \
  -d '{"room": "bedroom", "custom_tag": "server-b"}'
```

---

## 複数デバイスの一括登録例

```bash
for i in 1 2 3; do
  curl -s -X POST http://localhost:9100/devices \
    -H 'Content-Type: application/json' \
    -d "{
      \"device_id\": \"DUMMY00${i}\",
      \"attrs\": {\"name\": \"device_${i}\", \"room\": \"work\", \"shelf\": \"rack\", \"device\": \"pc\"},
      \"power_watts\": $((i * 50)),
      \"auto_jitter\": true,
      \"jitter_min\": 10.0,
      \"jitter_max\": 300.0
    }"
done
```
