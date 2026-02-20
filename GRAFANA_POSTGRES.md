# Grafana HA構成化計画 (PostgreSQL Backend)

## 目的
Grafana のダウンタイムゼロでの更新 (Rolling Update) と高可用性 (冗長化) を実現するため、バックエンドデータベースを現在の SQLite (ファイルベース) から PostgreSQL (RDBMS) に移行する。

## 現状の課題
- **SQLite の制約**: SQLite は単一ファイルへの書き込みロックが必要なため、複数の Grafana Pod から同時にマウントすることができない (ReadWriteOnce / Block Storage の制限)。
- **デプロイ戦略**: これにより、Deployment の戦略を `Recreate` (一度停止してから起動) にせざるを得ず、更新時に数秒〜数十秒のダウンタイムが発生する。

## 実装方針

### 1. データベース層の分離
Grafana の状態（ユーザー、ダッシュボード設定、アラート設定など）を外部の PostgreSQL に保存する。

- **構成**: 新たに PostgreSQL の StatefulSet を作成する、または既存の共有 DB インスタンスを利用する。
- **永続化**: PostgreSQL 自身は `PersistentVolumeClaim` を利用してデータを永続化する。

### 2. Grafana のステートレス化
Grafana 本体を「ステートレス」なアプリケーションとして構成する。

- **`grafana.ini` 設定変更**:
  - `[database]` セクションで `type = postgres` を指定し、接続情報を環境変数から読み込むように変更。
  - セッション情報なども DB または Redis (今回は DB で十分) に保存するように設定。
- **PVC の廃止**: Grafana Pod 自体には永続ボリューム (`/var/lib/grafana`) をマウントしない（または一時的なキャッシュ用のみにする）。

### 3. Kubernetes リソースの変更
- **Deployment**:
  - `replicas` を 1 から 2 以上に増やすことが可能になる。
  - `strategy` を `RollingUpdate` に変更する。
  - `readinessProbe` / `livenessProbe` は変更なし。
- **Secret**:
  - DB 接続情報 (ホスト、ユーザー、パスワード) を管理する Secret を追加。

## 移行ステップ (概略)

1. **DB 構築**: PostgreSQL の Deployment/StatefulSet および Service を作成。
2. **接続確認**: テスト用 Pod から DB への疎通確認。
3. **データ移行 (Optional)**:
   - 既存の SQLite (`grafana.db`) からデータを移行ツールで PostgreSQL に移す。
   - ※今回は IaC (ConfigMap) でダッシュボードを管理しているため、ユーザー作成などは捨てて新規作成でも良いかもしれない。
4. **Grafana 設定変更**: 環境変数を追加し、DB バックエンドを切り替えてデプロイ。
5. **スケールアウト**: レプリカ数を増やして冗長構成の動作確認。

## 期待される効果
- **無停止更新**: 設定変更やバージョンアップ時もサービスを継続可能。
- **対障害性**: Worker ノードの障害で Pod が再スケジュールされる際も、別の Pod がリクエストを処理できる。
