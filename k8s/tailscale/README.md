# Tailscale Operator

Tailscale Kubernetes Operator を Helm + Kustomize で管理する構成。
Grafana を Tailscale VPN 越しに HTTPS で公開する。

---

## ファイル構成

```
k8s/tailscale/
├── kustomization.yaml   # Kustomize + helmCharts 定義
├── helm-values.yaml     # Helm values（defaultTags 等。認証情報は含まない）
├── namespace.yaml       # tailscale Namespace
└── README.md            # このファイル
```

---

## 前提条件

### 1. ACL タグの設定

[Tailscale Admin Console の Access Controls](https://login.tailscale.com/admin/acls) に以下を追加・保存する:

```json
"tagOwners": {
  "tag:k8s-operator": [],
  "tag:k8s": ["tag:k8s-operator"]
}
```

### 2. OAuth クライアントの作成

[Admin Console の OAuth Clients](https://login.tailscale.com/admin/settings/oauth) で作成:

| カテゴリー | スコープ      | 設定値       | 用途                                                                      |
| ---------- | ------------- | ------------ | ------------------------------------------------------------------------- |
| Devices    | **Core**      | ✅ Read/Write | Tailnet 上に仒想デバイスを作成・削除する。これがないと何も動作しない      |
| Devices    | **Routes**    | ✅ Read/Write | LoadBalancer 公開・Subnet Router として動作するためにルート広報権限が必要 |
| Keys       | **Auth Keys** | ✅ Write      | プロキシ Pod が Tailnet に参加するための一時認証キーを自動生成する        |
| DNS        | DNS           | 推奨 Read    | MagicDNS 設定を読み取り、クラスター内からの Tailnet 名前解決に使用する    |

**Tags** フィールドに `tag:k8s-operator` を必ず指定すること。

生成された **Client ID** と **Client Secret** を控える。

### 3. .env ファイルへの認証情報追加

プロジェクトルートの `.env` に以下を追記:

```bash
TAILSCALE_CLIENT_ID=<取得した Client ID>
TAILSCALE_CLIENT_SECRET=<取得した Client Secret>
```

---

## インストール手順

```bash
# 1. Secret と Operator を一括インストール
make k8s-tailscale-install
```

内部では以下を実行している:

```bash
# Secret 生成（k8s/secret/tailscale-secret.yaml）
make k8s-secret-generate

# tailscale Namespace 作成（べき等）
kubectl create namespace tailscale --dry-run=client -o yaml | kubectl apply -f -

# 認証情報 Secret を apply
kubectl apply -f k8s/secret/tailscale-secret.yaml

# Helm Chart を Kustomize 経由でインストール
kustomize build --enable-helm k8s/tailscale | kubectl apply --server-side -f -
```

### インストール確認

```bash
kubectl get pods -n tailscale
# NAME                                    READY   STATUS    RESTARTS
# tailscale-operator-xxxxxxxxxx-xxxxx     1/1     Running   0

kubectl logs -n tailscale deploy/tailscale-operator -f
# エラーなく起動していれば成功
```

---

## 3. Grafana を Tailscale で公開する

各 overlay の `grafana-tailscale-patch.yaml` で Service を LoadBalancer に変更している。

| 環境       | ホスト名                 | URL                                               |
| ---------- | ------------------------ | ------------------------------------------------- |
| production | `smart-home-grafana`     | `https://smart-home-grafana.<tailnet>.ts.net`     |
| staging    | `smart-home-grafana-stg` | `https://smart-home-grafana-stg.<tailnet>.ts.net` |

### 確認

```bash
# EXTERNAL-IP が <hostname>.ts.net になれば成功
kubectl get svc -n smart-home prod-grafana
kubectl get svc -n smart-home-staging stg-grafana

# Tailscale Admin Console でも確認できる
# https://login.tailscale.com/admin/machines
```

---

## 4. アクセス

Tailscale に接続した端末のブラウザで以下にアクセス:

```
https://smart-home-grafana.<tailnet>.ts.net        # production
https://smart-home-grafana-stg.<tailnet>.ts.net    # staging
```

- Tailscale が HTTPS 証明書を自動発行するため、証明書エラーは発生しない
- Tailnet に参加していない端末からはアクセス不可（デフォルト）
- 公開インターネットへの公開が必要な場合は `tailscale.com/funnel: "true"` を設定する

---

`helm-values.yaml` のバージョン、またはタグを変更して再実行:

```bash
make k8s-tailscale-install
```
