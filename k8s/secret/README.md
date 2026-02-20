# Secret 管理

このディレクトリでは Kubernetes Secret を **テンプレート + `.env` から生成** する方式で管理する。

機密情報をリポジトリにコミットせず、`.gitignore` によって生成済みの `*.yaml`（テンプレート除く）を除外している。

---

## ファイル構成

```
k8s/secret/
├── README.md                              # このファイル
├── switchbot-secret.template.yaml         # SwitchBot 認証情報テンプレート
├── switchbot-secret.yaml                  # ⛔ 生成ファイル（gitignore 対象）
├── tailscale-secret.template.yaml         # Tailscale OAuth 認証情報テンプレート
└── tailscale-secret.yaml                  # ⛔ 生成ファイル（gitignore 対象）
```

---

## Secret 生成フロー

```
.env
  │
  ├─ SWITCHBOT_TOKEN / SWITCHBOT_SECRET
  │        └──→ switchbot-secret.template.yaml
  │                    └──→ switchbot-secret.yaml (make k8s-secret-generate)
  │
  └─ TAILSCALE_CLIENT_ID / TAILSCALE_CLIENT_SECRET
           └──→ tailscale-secret.template.yaml
                       └──→ tailscale-secret.yaml (make k8s-secret-generate)
```

---

## 利用手順

### 1. `.env` に認証情報を設定

```bash
# SwitchBot
SWITCHBOT_TOKEN=<your token>
SWITCHBOT_SECRET=<your secret>

# Tailscale
TAILSCALE_CLIENT_ID=<your client id>
TAILSCALE_CLIENT_SECRET=<your client secret>
```

### 2. Secret ファイルを生成

```bash
make k8s-secret-generate
# → k8s/secret/switchbot-secret.yaml
# → k8s/secret/tailscale-secret.yaml
```

### 3. Secret を使った各デプロイコマンド

| コマンド                     | 説明                                                   |
| ---------------------------- | ------------------------------------------------------ |
| `make k8s-deploy-production` | Smart Home 本番環境デプロイ（SwitchBot Secret を含む） |
| `make k8s-tailscale-install` | Tailscale Operator インストール/アップグレード         |
| `make k8s-secret-clean`      | 生成ファイルを削除                                     |

---

## テンプレートの書き方

新しい Secret を追加する場合は以下の手順に従う。

### Step 1: テンプレートファイルを作成

`k8s/secret/<name>-secret.template.yaml` を作成:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: <secret-name>
  namespace: <namespace>
type: Opaque
data:
  # make k8s-secret-generate によって自動挿入されます
  key: "{{MY_VALUE_BASE64}}"
```

プレースホルダー名は `{{` と `}}` で囲む。

### Step 2: `.env` に対応する変数を追加

```bash
# .env
MY_VALUE=<実際の値>
```

### Step 3: `Makefile` の `k8s-secret-generate` に sed 処理を追加

```makefile
# 既存の @source .env && \... ブロックの後に追記
@source .env && \
MY_VALUE_BASE64=$$(printf '%s' "$$MY_VALUE" | base64) && \
sed -e "s/{{MY_VALUE_BASE64}}/$$MY_VALUE_BASE64/g" \
    k8s/secret/<name>-secret.template.yaml > k8s/secret/<name>-secret.yaml
```

### Step 4: `k8s-secret-clean` のクリーン対象に追加

```makefile
@rm -f k8s/secret/<name>-secret.yaml
```

### Step 5: kustomization または make コマンドから参照

- `k8s/overlays/production/kustomization.yaml` の `resources:` に追加する場合:
  ```yaml
  resources:
    - ../../secret/<name>-secret.yaml
  ```
- または `kubectl apply -f k8s/secret/<name>-secret.yaml` で個別 apply する。

---

## TODO

- [ ] **Sealed Secrets / External Secrets への移行検討**  
  現在は `.env` + `make` でローカル生成しているが、GitOps（ArgoCD）で完全自動化するには
  [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets) や
  [External Secrets Operator](https://external-secrets.io/) への移行が望ましい。
  詳細は [`SEALED_SECRET.md`](../../SEALED_SECRET.md) を参照。

- [ ] **`.env.example` の整備**  
  `.env.example` に全変数のテンプレートを用意し、新規セットアップ時の手順を簡略化する。

- [ ] **Secret rotation の仕組み**  
  SwitchBot / Tailscale の認証情報が更新された場合の手順（`make k8s-secret-generate` → 各 apply）をドキュメント化する。
