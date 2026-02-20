# Grafana - ダッシュボード

## 役割

Grafana は本システムの**可視化レイヤー**として動作する。

- VictoriaMetrics を datasource として PromQL でメトリクスを取得・グラフ化
- ダッシュボードおよびデータソースは ConfigMap による **Provisioning** で自動設定される（GUI での手動設定は不要）
- 外部公開が必要な場合は Tailscale Operator を使用する（[手順](../../tailscale/README.md)）

---

## 構成ファイル

| ファイル                                   | 内容                                   |
| ------------------------------------------ | -------------------------------------- |
| `deployment.yaml`                          | Grafana コンテナのデプロイ設定         |
| `service.yaml`                             | ClusterIP サービス（ポート 3000）      |
| `configmap.yaml`                           | データソース Provisioning 設定         |
| `configmap-dashboard-provisioner.yaml`     | ダッシュボード Provisioning 設定       |
| `configmap-dashboard-device-overview.yaml` | デバイス概要ダッシュボード定義（JSON） |
| `pvc.yaml`                                 | Grafana データ永続化用 PVC             |
| `kustomization.yaml`                       | このコンポーネントのリソース一覧       |

本番環境ではデータソースの URL が  
`k8s/overlays/production/grafana-datasource-patch.yaml` で `http://prod-victoriametrics:8428` に上書きされる。

---

## デプロイ

```bash
# 本番環境全体をデプロイ
make k8s-deploy-production

# 状態確認
kubectl get pods -n smart-home -l app=grafana
```

---

## 動作確認・デバッグ

### UI へのアクセス

```bash
kubectl port-forward -n smart-home svc/prod-grafana 3000:3000
```

ブラウザで http://localhost:3000 を開く。  
初期認証情報: `admin` / `admin`

### ヘルスチェック

```bash
curl http://localhost:3000/api/health
# {"commit":"...","database":"ok","version":"..."}
```

---

## Tailscale での外部公開

VPN 越しに Grafana に安全にアクセスする場合は  
[k8s/tailscale/README.md](../../tailscale/README.md) を参照。

---

## 注意事項

- `GF_SERVER_ROOT_URL` は Tailscale などで公開する際に実際の URL に変更すること
- ダッシュボードを GUI で編集した内容は PVC に保存されるが、ConfigMap の JSON が
  次のデプロイで上書きされる可能性がある。変更を永続化するには ConfigMap の JSON を更新すること
- PVC を削除すると GUI で保存したプラグイン・設定・ユーザーが失われる
