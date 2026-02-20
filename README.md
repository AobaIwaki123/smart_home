# スマートホーム監視基盤

SwitchBot Plug Mini の消費電力を収集・可視化するシステム。  
Prometheus 互換メトリクスを VictoriaMetrics に蓄積し、Grafana で可視化する。

## システム概要

```
SwitchBot API
     │
     ▼
 [Exporter]  ←── Python / Prometheus format
     │
     ▼
[VictoriaMetrics]  ←── 時系列DB（スクレイプ担当も兼任）
     │
     ▼
  [Grafana]  ←── ダッシュボード
```

開発・動作確認時は、実デバイスの代わりに `dummy-exporter` がダミーメトリクスを生成する。

## ディレクトリ構成

```sh
smart_home/
├── README.md               # このファイル
├── .env.example            # 環境変数テンプレート（機密情報は含まない）
├── Makefile                # ビルド・デプロイ・テストのタスク定義
├── k8s/                    # Kubernetes マニフェスト
│   ├── base/               # 全環境共通設定（Kustomize base）
│   │   ├── kustomization.yaml
│   │   ├── namespace/      # smart-home Namespace
│   │   ├── exporter/       # SwitchBot データ収集エンジン
│   │   ├── dummy-exporter/ # 開発用ダミーメトリクス生成器
│   │   ├── victoriametrics/# 時系列データベース
│   │   ├── grafana/        # ダッシュボード
│   │   ├── bff/            # (未使用) バックエンド API
│   │   └── frontend/       # (未使用) フロントエンド UI
│   └── overlays/           # 環境差異設定
│       └── production/     # 本番環境（実 SwitchBot API 使用）
├── services/               # アプリケーション実装
│   ├── exporter/           # データ収集スクリプト (Python)
│   │   ├── src/            # メインロジック
│   │   ├── tests/          # pytest テスト
│   │   ├── scripts/        # 開発用ユーティリティ
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── dummy-exporter/     # ダミーメトリクス生成器 (Python)
│   │   ├── src/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── bff/                # (未実装) バックエンド API (FastAPI)
│   │   ├── src/
│   │   ├── migrations/     # SQLite スキーマ管理
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── frontend/           # (未実装) ダッシュボード UI (Next.js)
│       ├── src/
│       ├── public/
│       ├── Dockerfile
│       └── package.json
└── scripts/                # 開発・運用補助スクリプト
```

## クイックスタート

```bash
# 本番環境（.env に SWITCHBOT_TOKEN/SECRET を設定済みの前提）
make k8s-deploy-production

# 状態確認
kubectl get pods -n smart-home
```

詳細は [k8s/README.md](k8s/README.md) を参照。

## 参考

- [職場のプロジェクトに必ず配置しちゃうMakefileの話 - Zenn](https://zenn.dev/loglass/articles/0016-make-makefile)