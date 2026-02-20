# Tailscale Operator で Grafana を公開する

Tailscale Operator を Kubernetes クラスターに導入し、Grafana を Tailscale VPN 越しに
HTTPS で安全に公開する手順。

---

## 前提条件

| 項目                 | 内容                                             |
| -------------------- | ------------------------------------------------ |
| Tailscale アカウント | https://login.tailscale.com でサインアップ済み   |
| Tailnet              | 自分の tailnet（例: `example.ts.net`）が存在する |
| Helm v3              | インストール済み                                 |
| kubectl              | `smart-home` クラスターへのアクセス権がある      |
| Grafana              | `k8s/overlays/production` でデプロイ済み         |

---

## 1. OAuth クライアントの作成

Tailscale Admin Console でオペレーター用の OAuth クライアントを作成する。

1. https://login.tailscale.com/admin/settings/oauth にアクセス
2. **Generate OAuth client** をクリック
3. スコープを以下のとおり設定する

   | カテゴリ | スコープ      | 設定値       | 用途                                                                      |
   | -------- | ------------- | ------------ | ------------------------------------------------------------------------- |
   | Devices  | **Core**      | ✅ Read/Write | Tailnet 上に仮想デバイスを作成・削除する。これがないと何も動作しない      |
   | Devices  | **Routes**    | ✅ Read/Write | LoadBalancer 公開・Subnet Router として動作するためにルート広報権限が必要 |
   | Keys     | **Auth Keys** | ✅ Write      | プロキシ Pod が Tailnet に参加するための一時認証キーを自動生成する        |
   | DNS      | DNS           | 推奨 Read    | MagicDNS 設定を読み取り、クラスター内からの Tailnet 名前解決に使用する    |

4. **タグ（ACL Tag）を事前に設定する**

   > **重要**: OAuth クライアントにタグが紐付いていない場合、Operator 起動時に
   > `403: calling actor does not have enough permissions` が発生する。

   Tailscale Admin Console の **Access Controls** (ACL) に以下を追加:

   ```json
   "tagOwners": {
     "tag:k8s-operator": [],
     "tag:k8s": ["tag:k8s-operator"]
   }
   ```

   - `tag:k8s-operator`: Operator 自体のタグ（OAuth クライアントに紐付ける）
   - `tag:k8s`: Operator が管理するデバイスに付与されるタグ（`tag:k8s-operator` が所有者）

   OAuth クライアント作成時に `tag:k8s-operator` を **Tags** フィールドで指定する。

5. 生成された **Client ID** と **Client Secret** を控える

---

## 2. Tailscale Operator のインストール

```bash
# Helm リポジトリ追加
helm repo add tailscale https://pkgs.tailscale.com/helmcharts
helm repo update

# Operator 用ネームスペース作成
kubectl create namespace tailscale

# Operator インストール（Helm が operator-oauth Secret を自動作成する）
helm upgrade --install tailscale-operator tailscale/tailscale-operator \
  --namespace tailscale \
  --set-string oauth.clientId=<CLIENT_ID> \
  --set-string oauth.clientSecret=<CLIENT_SECRET> \
  --set "operatorConfig.defaultTags[0]=tag:k8s" \
  --set "proxyConfig.defaultTags=tag:k8s" \
  --wait
```

> **注意**: `kubectl create secret` で `operator-oauth` を手動作成してから Helm を実行すると
> `invalid ownership metadata` エラーが発生する。Secret の作成は Helm に任せること。

インストール確認:

```bash
kubectl get pods -n tailscale
# NAME                                    READY   STATUS    RESTARTS
# tailscale-operator-xxxxxxxxxx-xxxxx     1/1     Running   0
```

---

## 3. Grafana Service を Tailscale で公開する

`k8s/base/grafana/service.yaml` の Service に以下のアノテーションを追加することで、
Tailscale Operator が自動的に VPN 上の DNS エントリを作成する。

### オプション A: 既存 Service をアノテーションで公開（推奨）

production overlay 内に Service パッチファイルを作成する:

```bash
# k8s/overlays/production/grafana-tailscale-patch.yaml
```

```yaml
apiVersion: v1
kind: Service
metadata:
  name: grafana
  annotations:
    # Tailscale Operator がこのアノテーションを検知して VPN ホスト名を割り当てる
    tailscale.com/expose: "true"
    tailscale.com/hostname: "smart-home-grafana"   # <tailnet> 上のホスト名
spec:
  type: LoadBalancer
  loadBalancerClass: tailscale
```

`k8s/overlays/production/kustomization.yaml` の `patches` に追記:

```yaml
patches:
  - path: deployment-patch.yaml
  - path: victoriametrics-config-patch.yaml
    target:
      kind: ConfigMap
      name: victoria-metrics-scrape-config
  - path: grafana-datasource-patch.yaml
    target:
      kind: ConfigMap
      name: grafana-datasources
  - path: grafana-tailscale-patch.yaml   # ← 追加
    target:
      kind: Service
      name: grafana
```

### オプション B: 専用の Tailscale Ingress を使う

Tailscale Operator v1.56+ では `Ingress` リソースが利用できる:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: grafana-tailscale
  namespace: smart-home
  annotations:
    tailscale.com/funnel: "false"   # Funnel は公開インターネット向け。VPN 内のみなら false
spec:
  defaultBackend:
    service:
      name: prod-grafana
      port:
        number: 3000
  ingressClassName: tailscale
```

---

## 4. デプロイと確認

```bash
# 変更を反映
make k8s-deploy-production

# Tailscale ノードとして認識されているか確認
kubectl get svc -n smart-home prod-grafana
# EXTERNAL-IP が <tailnet hostname>.ts.net になれば成功

# または Tailscale Admin Console で確認
# https://login.tailscale.com/admin/machines
```

---

## 5. Grafana の ROOT_URL を更新する

Tailscale 経由でアクセスするため、Grafana の `GF_SERVER_ROOT_URL` を実際の URL に
合わせる必要がある。`k8s/overlays/production/deployment-patch.yaml` に以下を追記:

```yaml
- name: GF_SERVER_ROOT_URL
  value: "https://smart-home-grafana.<tailnet>.ts.net"
```

---

## 6. アクセス

Tailscale に接続した端末のブラウザで以下にアクセス:

```
https://smart-home-grafana.<tailnet>.ts.net
```

- Tailscale が HTTPS 証明書を自動発行するため、証明書エラーは発生しない
- Tailnet に参加していない端末からはアクセス不可（デフォルト）
- 公開インターネットへの公開が必要な場合は `tailscale.com/funnel: "true"` を設定する

---

## トラブルシューティング

```bash
# Operator のログ確認
kubectl logs -n tailscale deploy/tailscale-operator -f

# Service が Tailscale に登録されているか
kubectl describe svc -n smart-home prod-grafana

# Tailscale ノード一覧（CLI がある場合）
tailscale status
```

| 症状                                    | 確認ポイント                                                                                                                                                                                                                         |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `EXTERNAL-IP` が `<pending>` のまま     | Operator Pod のログで OAuth 認証エラーを確認                                                                                                                                                                                         |
| `403: does not have enough permissions` | ① ACL の `tagOwners` に `tag:k8s-operator` と `tag:k8s` の2タグ構造が設定されていない、または ② OAuth クライアントに `tag:k8s-operator` タグが紐付いていない。タグは作成時のみ設定可能なため、OAuth クライアントを作り直す必要がある |
| `invalid ownership metadata` (Helm)     | `operator-oauth` Secret が手動作成済み。Secret を削除するか Helm ラベル/アノテーションを付与してから再実行する                                                                                                                       |
| 証明書エラー                            | Tailscale MagicDNS・HTTPS が tailnet で有効か確認 (`Admin > DNS`)                                                                                                                                                                    |
| VPN 外からアクセスしたい                | `tailscale.com/funnel: "true"` を設定し Funnel を有効化                                                                                                                                                                              |
