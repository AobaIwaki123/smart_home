# Scripts Directory

このディレクトリには、プロジェクト開発を支援するユーティリティスクリプトが格納されています。

## `help.awk`

### 概要
`Makefile` のターゲットとその説明をパースし、整形されたヘルプメッセージを標準出力に表示するための AWK スクリプトです。
`make help` コマンド実行時に呼び出されます。

### 仕組み
`Makefile` 内の特定のパターンにマッチする行を抽出・整形します。

1. **ターゲット記述**: `target: ## description` の形式
   - `target` をシアン色で表示
   - `description` をその右側に表示
2. **セクション区切り**: `## Section Name ##` の形式
   - `Section Name` を太字でセクション見出しとして表示

### 使用方法 (Makefile)

`.DEFAULT_GOAL := help` と `.PHONY: help` を設定し、以下のように記述します。

```makefile
help: ## Show this help
	@awk -f scripts/help.awk $(MAKEFILE_LIST)
```

そして、各ターゲットやセクションにコメントを追加します。

```makefile
## Python Environment ##

pip: ## Install python dependencies
	pip install -r requirements.dev.txt
```
