# ディレクトリ構成

```sh
smart_home/
├── README.md               # プロジェクト全体の概要・仕様書
├── .env.example            # 環境変数のテンプレート（機密情報は含まない）
├── Makefile                # ビルド・デプロイ・テストのタスク定義
├── k8s/                    # Kubernetesマニフェスト（GitOpsを見据えて分離）
│   ├── base/               # 全環境共通設定
│   │   ├── victoria-metrics/
│   │   ├── exporter/
│   │   ├── bff/
│   │   └── frontend/
│   └── overlays/           # モック用、本番用などの環境差異
│       ├── mock/
│       └── production/
├── services/               # アプリケーション本体
│   ├── exporter/           # データ収集スクリプト (Python)
│   │   ├── src/            # メインロジック
│   │   ├── tests/          # 認証テスト用スクリプト等
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── bff/                # バックエンド API (FastAPI)
│   │   ├── src/
│   │   ├── migrations/     # SQLiteのスキーマ管理
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── frontend/           # ダッシュボード UI (Next.js)
│       ├── src/
│       ├── public/
│       ├── Dockerfile
│       └── package.json
└── scripts/                # 開発・運用補助スクリプト
```