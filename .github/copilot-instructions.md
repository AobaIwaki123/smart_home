# GitHub Copilot Instructions for smart_home

## プロジェクト概要

SwitchBot Plug Mini の消費電力を Prometheus/VictoriaMetrics に収集するシステム。

---

## コーディングルール

### API リクエスト全般

**SwitchBot API を含む外部 HTTP API を呼び出すコードを書く際は、必ずレスポンスヘッダーから API レート制限情報を取得・記録すること。**

取得すべきヘッダー：

| ヘッダー名 | 内容 |
|---|---|
| `x-ratelimit-limit` | 1日の最大コール数 |
| `x-ratelimit-remaining` | 本日の残り回数 |
| `x-ratelimit-reset` | リセット時刻（エポック ms） |

#### 推奨パターン（httpx / AsyncClient）

```python
resp = await client.get(url, headers=headers, timeout=10.0)

# 必須: レート制限ヘッダーを記録する
remaining = resp.headers.get("x-ratelimit-remaining")
if remaining is not None:
    API_REMAINING.set(int(remaining))

resp.raise_for_status()
```

- `remaining` が `None` の場合（ヘッダーなし）はスキップしてよいが、警告ログを出すことを推奨。
- Prometheus Gauge `API_REMAINING` への記録は省略しないこと。

### ロギング

- API 呼び出し成功時: `logging.info` でデバイス ID と取得値を出力する。
- API 呼び出し失敗時: `logging.error` で例外内容を出力し、 `DEVICE_UP` を `0` にセットする。
- レート制限が残り **100 以下** になったら `logging.warning` を出すこと。

```python
if remaining is not None and int(remaining) <= 100:
    logging.warning(f"API rate limit low: {remaining} calls remaining")
```

### Prometheus メトリクス

- メトリクス削除（`.remove()`）は必ず `try/except KeyError` で囲む。
- 新しい Gauge を定義するときはラベル設計をレビューし、カーディナリティが爆発しないことを確認する。

### 型ヒント

- 関数定義には原則として型ヒントを付与する（`src/main.py` の既存関数を参照）。

---

## ディレクトリ構成の注意

- `scripts/` はユーティリティ専用。メトリクス Gauge には直接触らない。
- テストは `tests/` に配置し、`respx.mock` でモックする（実 API は叩かない）。
