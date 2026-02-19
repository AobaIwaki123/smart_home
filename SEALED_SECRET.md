## Sealed Secrets 導入の戦略的ロードマップ

### 1. 基盤の構築（Setup Phase）

まずは「封印」と「解読」ができる環境を整えます。

* **Controller の設置**: クラスター内に「解読のプロ（コントローラー）」を常駐させます。
* **鍵のペアリング**: クラスターが持つ「公開鍵（封印用）」をローカル（Mac）に取得し、自分だけが封印できる状態を作ります。

### 2. 封印対象の選定（Identification Phase）

何を Git に「生」で載せてはいけないかを整理します。今回のプロジェクトでは以下の 2 点がメインです。

* **Authentication (認証情報)**: `SWITCHBOT_TOKEN`, `SWITCHBOT_SECRET`
* これらは「他人に知られると操作される」致命的な情報。


* **Topology & Privacy (物理構成)**: `devices.json` (Device IDs, Parent/Child 階層)
* これらは「家の構造」が透けて見えるプライバシー情報。



### 3. 変換ワークフローの確立（Transformation Phase）

「生の Secret」を「封印された Secret」へ変換する手順をルーチン化します。

* **Raw Secret 生成**: ローカルでのみ、一時的に生の YAML を作成。
* **Sealing (封印)**: `kubeseal` コマンドで、クラスターの公開鍵を使って暗号化。
* **Discard (破棄)**: 暗号化が終わったら、**生の YAML は即座に削除**（Git に入れない）。

### 4. Git 運用への統合（GitOps Phase）

暗号化されたファイルをリポジトリの中心に据えます。

* **Public 化への検証**: GitHub に Push された `SealedSecret` が、クラスター内で正しく元の `Secret` に復元され、Exporter が起動するかを確認。
* **履歴のクレンジング**: 必要であれば、過去の Git ログからデバイス ID が含まれるコミットを削除し、完全にクリーンな状態で Public 化へ。

---

## 🔐 暗号化の対象：マインドマップ

Aoba さんのシステムで「封印」すべきものは、以下の通りです。

1. **SwitchBot Credentials**: クラウド API へのアクセス権。
2. **Device Config**: 「どの ID がどこにあるか」という家の間取り図に近いデータ。
3. **Infrastructure Secrets** (将来): VictoriaMetrics の認証設定や、BFF が SQLite を暗号化する場合の鍵など。
