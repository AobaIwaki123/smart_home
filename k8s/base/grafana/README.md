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

## ダッシュボードの追加方法

新しいダッシュボード（JSON）を追加する際は、以下の手順に従ってください。

1. **ConfigMap の作成**:
   新しいダッシュボードの JSON 定義を含む ConfigMap (例: `configmap-dashboard-new.yaml`) を作成します。
   `metadata.name` は既存のものと重複しないように注意してください。

2. **kustomization.yaml への追加**:
   `resources` リストに作成したファイルを追加します。

   ```yaml
   resources:
     - configmap-dashboard-device-overview.yaml
     - configmap-dashboard-room-overview.yaml
     - configmap-dashboard-new.yaml  # 追加
   ```

3. **Deployment の更新 (重要)**:
   すべてのダッシュボード定義ファイルをコンテナ内の同一ディレクトリ (`/var/lib/grafana/dashboards`) に配置するため、**Projected Volume** を使用しています。
   `deployment.yaml` 内の `volumes` 設定にある `dashboards` ボリュームの `sources` リストに新しい ConfigMap を追加してください。

   ```yaml
   volumes:
     - name: dashboards
       projected:
         sources:
           - configMap:
               name: grafana-dashboard-device-overview
           - configMap:
               name: grafana-dashboard-room-overview
           - configMap:                 # 追加
               name: grafana-dashboard-new
   ```

   ※ 個別の `configMap` ボリュームとしてマウントすると、ディレクトリが上書きされて他のダッシュボードが見えなくなるため、必ず `projected` リストに追加してください。

---

