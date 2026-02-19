# SwitchBot Power Exporter

## 概要

本コンポーネントは、SwitchBotデバイスから取得した物理情報を Prometheus 形式のメトリクスに変換し、外部（VictoriaMetrics 等）へ公開するブリッジです。
「おうちk8s」インフラにおける可視化基盤のデータ源泉として機能します。

## 設計思想

* **抽象化された取得元 (Multi-Transport):** データの取得経路（Cloud API / BLE / Mock）を抽象化し、実行環境やデバイスの特性に応じて柔軟に切り替え可能とします。
* **階層的コンテキストの付与:** 無機質なデバイスIDに対し、論理的な階層（House / Room / Shelf）をメタデータとして注入し、意味のあるデータへと昇華させます。
* **信頼性優先 (Stale Marker Policy):** 取得失敗時に古い値を維持せず、メトリクスを明示的に削除することで、グラフ上での「沈黙」を正しく表現します。
* **リソース効率:** Raspberry Pi 等の低リソースノードでの動作を前提とし、最小限の依存関係とフットプリントで動作させます。

## メトリクス仕様 (Public Interface)

公開されるメトリクスは以下の通りです。単位はすべて標準的な物理単位に基づきます。

| メトリクス名                       | 型      | 説明                                                               |
| ---------------------------------- | ------- | ------------------------------------------------------------------ |
| `switchbot_power_watts`            | Gauge   | 瞬時電力。単位はワット (W)。                                       |
| `switchbot_energy_total_kwh`       | Counter | 累積電力量。単位はキロワット時 (kWh)。コスト計算のマスターデータ。 |
| `switchbot_device_up`              | Gauge   | デバイスの到達性。1: 正常, 0: 異常。                               |
| `switchbot_api_requests_remaining` | Gauge   | 外部APIの残リクエスト可能回数（クォータ監視）。                    |

## メタデータ構造 (Labels)

集計の柔軟性を担保するため、すべての電力メトリクスには以下の共通ラベルを付与します。

* `house`: 設置された建物（例: `myhome`）
* `room`: 設置された部屋（例: `work_room`）
* `shelf`: 設置された棚・区画（例: `rack_1`）
* `device`: 接続されている機器（例: `pc`, `multi-tap-a`）
* `device_name`: プラグの論理名（SwitchBot デバイス名、例: `プラグミニ_da`）
* `device_id`: デバイスの物理固有ID（例: MACアドレス）
* `source`: データ取得ソース（例: `cloud`, `ble`, `mock`）

## 動作要件

* **Configuration:** デバイスIDと階層情報のマッピングは、外部設定（ConfigMap等）から注入される必要があります。
* **Security:** 認証情報（API Token等）は、環境変数を介して外部（Kubernetes Secrets等）から安全に提供される必要があります。
* **Deployment:** x86 および ARM アーキテクチャの双方で動作するマルチアーキテクチャ・コンテナとして提供されます。
