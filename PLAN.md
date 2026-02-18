
# SwitchBot電力監視システム（PPMS）最終仕様書

## 1. システム概要

SwitchBot プラグミニから取得した電力量データを、論理的な階層（家・部屋・棚）に基づき可視化・分析する。1ユーザー（自分）専用とすることで、認証実装を簡略化しつつ、インフラとしての堅牢性とデータの信頼性を最大化する。

---

## 2. システムアーキテクチャ

全コンポーネントを Kubernetes 上に展開し、ハードウェア特性に応じたノード配置を行う。

### 2.1 データ収集層 (Exporter)

* **構成:** Python (multi-arch対応)
* **Fetcher設計:** * `CloudFetcher`: API v1.1 署名認証を用いてクラウドから取得。
* `BleFetcher`: `bleak` 等を用い、Bluetooth経由でローカル取得（将来拡張）。


* **階層注入:** 外部YAML設定ファイル（ConfigMap）を読み込み、デバイスIDに `room` / `shelf` などの階層ラベルを付与して Prometheus 形式で出力。

### 2.2 データ蓄積層 (VictoriaMetrics)

* **構成:** `vmsingle` (シングルノード構成)
* **役割:** 時系列データの永続化。Prometheus互換クエリを提供。
* **保存戦略:** 高圧縮・長期保存。1年以上のログを保持。

### 2.3 ビジネスロジック層 (BFF / FastAPI)

* **構成:** FastAPI + SQLite
* **SQLiteの責務:** * `unit_prices`: 電気代単価の履歴管理（単価、適用開始/終了日時）。
* `device_meta`: デバイスの表示名や詳細情報の保持。


* **計算処理:** 特定期間の `kwh_counter` の増分に対し、該当期間の単価を動的に乗算してコストを算出。

### 2.4 可視化層 (Frontend / Next.js)

* **構成:** Next.js (TypeScript)
* **UI機能:** 階層ドリルダウン、積算電気代表示、デバイス死活状態表示。

---

## 3. データモデル定義

### 3.1 メトリクス

| メトリクス名 | 型 | 説明 |
| --- | --- | --- |
| `switchbot_power_watts` | Gauge | 現在の消費電力 |
| `switchbot_energy_total_kwh` | Counter | 累積電力量（コスト計算のマスターデータ） |
| `switchbot_device_up` | Gauge | 死活監視 (1: OK, 0: NG) |

### 3.2 ラベル構成

`{house="myhome", room="work", shelf="rack_1", device="server", source="cloud/ble"}`

---

## 4. インフラ・セキュリティ仕様

### 4.1 ネットワーク & 認証

* **外部アクセス:** **Tailscale Kubernetes Operator** を採用。
* **アクセス制御:** フロントエンドのみを `ts.net` ドメインで公開。VPN接続者（自分）のみがアクセス可能なため、アプリ層での ID/Pass 認証は実装しない。
* **内部通信:** ClusterIP を使用し、BFFやDBはクラスター外から直接アクセス不能とする。

### 4.2 ノード戦略 (Mixed Arch)

* **x86 VM (Proxmox):** VictoriaMetrics, BFF, Frontend を配置。
* **ARM Pi:** `BleFetcher` を利用する Exporter を `nodeSelector` で優先配置。
* **USB Passthrough:** VMでBLEを使う場合、Proxmox側でアダプタをパススルー設定する。

### 4.3 信頼性設計

* **Stale Marker:** API取得失敗時は値をキャッシュせず、メトリクスを一時停止させることで、グラフ上の「データ欠損」を明示する。
* **Secret管理:** APIトークンやシークレットは **Kubernetes Secret** から環境変数として注入。

---

## 5. 運用管理

* **単価操作:** BFFのAPI経由で、UIから単価の追加・履歴削除を可能にする。


---

### 1. 仕様書の追記・修正

#### メトリクスの追加

* **`switchbot_api_requests_remaining` (Gauge)**
* **役割:** 当日の残リクエスト回数を可視化。
* **詳細:** APIレスポンスヘッダーに含まれる情報をパースして保持。これが一定値を下回ったら収集間隔を自動で伸ばす、といった「サバイバルモード」の実装も視野に入ります。



#### デバイスステータスのパース注意点

* **`weight` フィールドの扱い:**
* SwitchBot Plug Mini (JP/US) のステータス取得において、電力値（W）は **`weight`** というキーで返却されます。
* **注意:** `wattage` というフィールドは存在しない、あるいは他のモデル用である可能性があるため、パース時は `weight` を主軸に据えることを明記します。
* ※電圧は `voltage`、電流は `electricCurrent` です。



---

### 2. 開発を簡略化するための戦略

「車輪の再発明」を避け、本質的な「階層管理」と「UI」に注力するための簡略化案です。

#### B. Exporter化：`prometheus_client` の活用

`/metrics` エンドポイントを手動で文字列生成するのは非効率です。

* **既存実装:** Python 公式の `prometheus_client`
* **簡略化:** `Gauge` や `Counter` のオブジェクトを定義し、値を `set()` するだけで、Prometheus 互換のフォーマットを自動生成・公開してくれます。

#### C. BFFの基盤：`FastAPI` + `SQLAlchemy`

SQLiteの操作とAPI化を最速で終わらせます。

* **簡略化:** Pydantic モデルを定義すれば、リクエストのバリデーションと Swagger UI（APIドキュメント）が自動生成されます。単価管理の CRUD 操作を数行で実装可能です。

---

### 3. 修正後の構成図（ライブラリ反映版）

2. **VictoriaMetrics:** `vmsingle` (StatefulSet) でデータを蓄積。
3. **BFF:** `FastAPI` + `SQLAlchemy` で SQLite (単価マスタ) を管理し、PromQL を発行。
4. **Frontend:** `Next.js` で階層型ダッシュボードを表示。

---

### 次のステップ：実装の開始

仕様が完全に固まりました。Aobaさんの「おうちk8s」に命を吹き込む最初のステップとして、まずは最も重要な **「SwitchBot API v1.1 対応の Python Exporter プロトタイプ」** を作成しましょう。

具体的には、以下のコードを準備できます：

1. **API v1.1 の署名（Signature）生成ロジック**
2. **`switchbot_device_up` を含む Prometheus 形式の出力処理**

この実装案を提示してもよろしいでしょうか？あるいは、先に **Ansible や k8s マニフェストの雛形** を固めたいですか？