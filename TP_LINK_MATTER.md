## TP-Link Power Monitoring Dual-Exporter ロードマップ

### フェーズ 1: プロジェクト基盤の構築 (Scaffolding)

既存の SwitchBot 実装から「成功したパターン」を各サービスへ移植し、開発環境を整えます。

* **サービスの分離:**
* `services/tp-link-native-exporter` および `services/tp-link-matter-exporter` のディレクトリ作成。
* SwitchBot 版の `collector.py` (Custom Collector 構造) をコピーし、インターフェースをモック化。


* **依存関係の定義:**
* Native 版: `python-kasa` (asyncio) を採用。
* Matter 版: `python-matter-server` (client SDK) を採用。


* **共通設定ファイルの設計:**
* `device_id` (MAC) と `house/room/shelf/device` を紐付ける YAML スキーマを統一。



### フェーズ 2: プロトコル別コア実装 (Core Development)

それぞれの通信特性に合わせたデータ取得ロジックを実装します。

* **Native 系統 (The Specialist):**
* **KLAP Auth:** Tapo 独自のセキュアプロトコルによる認証ハンドシェイクの実装。
* **Metric Extraction:** `emeter` プロパティから `watts`, `voltage`, `current` を抽出。
* **Stale Marker Policy:** `DeviceOffline` 例外をキャッチした際、当該メトリクスを明示的に削除し「沈黙」を表現。


* **Matter 系統 (The Standard):**
* **Matter Server 構築:** K8s 上に `matter-server` をデプロイ（サイドカーまたは共有サービス）。
* **Cluster Mapping:** Matter 1.3 以降の `ElectricalPowerMeasurement` クラスターから属性値を購読。
* **Standardization:** 単位（mW 単位など）を、SwitchBot 版と同じ W 単位へ正規化。



### フェーズ 3: Kubernetes & ArgoCD 統合 (Deployment)

作成した Exporter をクラスターに投入し、モニタリングパイプラインを確立します。

* **Multi-arch Build:**
* GitHub Actions 等で `linux/amd64` および `linux/arm64` のコンテナイメージをビルド。


* **K8s Manifest 実装:**
* `k8s/base` にそれぞれの Deployment, Service, ServiceMonitor を定義。
* `ServiceMonitor` に `protocol: "native"` と `protocol: "matter"` のラベルを付与。


* **ArgoCD 同期:**
* `argocd/app.yaml` に新設 2 サービスを追加し、自動デプロイを開始。



### フェーズ 4: 比較評価と最終選定 (Analysis & Decision)

同一デバイスから取得される 2 系統のデータを Grafana 上で突き合わせます。

* **評価項目のモニタリング (PromQL):**
* **精度比較:** `tplink_native_power_watts` vs `tplink_matter_power_watts` の差分確認。
* **遅延測定:** Scrape 時間 (`scrape_duration_seconds`) の比較。
* **安定性:** ネットワーク瞬断時やデバイス再起動時の復帰プロセスの堅牢性。


* **最終選定:**
* 「取得項目の多さと安定性（Native）」か「規格の汎用性と将来性（Matter）」かを、Aoba さんの実際の運用データに基づき判断。



---

## 期待される成果物 (Outputs)

1. **統一された Grafana ダッシュボード:** メーカーやプロトコルを意識せず、`room` や `device` ラベルでフィルタリング可能な電力ビュー。
2. **再利用可能な Collector 基盤:** 今後、他メーカーのプラグが増えた際も、同様のパターンで迅速に追加可能。
3. **高精度な電力ログ:** Stale Marker Policy により、偽陽性のないクリーンな VictoriaMetrics データベース。

---

### 実装に向けた最初のアクション

まずは **Native 版の `collector.py` に `python-kasa` を組み込み、手元の Tapo P110 から 1 回分の電力値を抜く最小構成** から着手するのが、最も不確実性を早く解消できます。

このロードマップに沿って、具体的な **Native 版の Python スケルトンコード（SwitchBot 版の構成を踏襲したもの）** を作成しましょうか？