"""
dummy-exporter: Grafana テスト用の擬似データ生成 Prometheus Exporter

REST API でデバイスの追加/削除/属性編集・電力値制御・UP/DOWN を管理し、
/metrics エンドポイントで Prometheus フォーマットを返す。

使用するメトリクス名は本番 exporter と同一なので、既存の Grafana ダッシュボードで動作する。
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, JSONResponse
from prometheus_client import (
    CollectorRegistry,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# ロギング
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prometheus Registry（本番 exporter と衝突しないよう独立した Registry を使用）
# ---------------------------------------------------------------------------
REGISTRY = CollectorRegistry(auto_describe=False)

POWER_WATT = Gauge(
    "switchbot_power_watts",
    "Current power usage in Watts",
    ["room", "shelf", "device", "device_name", "device_id", "parent_id"],
    registry=REGISTRY,
)

DEVICE_UP = Gauge(
    "switchbot_device_up",
    "Device availability (1: OK, 0: NG)",
    ["device_id"],
    registry=REGISTRY,
)

API_REMAINING = Gauge(
    "switchbot_api_requests_remaining",
    "Remaining API calls for the day (dummy: fixed 9999)",
    registry=REGISTRY,
)
API_REMAINING.set(9999)

# ---------------------------------------------------------------------------
# デバイスストア（インメモリ）
# ---------------------------------------------------------------------------
# key: device_id (str)
# value: {
#   "device_id": str,
#   "power_watts": float,
#   "up": bool,
#   "auto_jitter": bool,
#   "jitter_min": float,
#   "jitter_max": float,
#   "attrs": dict[str, Any]   ← name/room/shelf/device/parent_id + 任意の追加属性
# }
_devices: dict[str, dict[str, Any]] = {}


def _std_attr(attrs: dict[str, Any]) -> tuple[str, str, str, str, str]:
    """Prometheus ラベルに使う標準属性を attrs から取得する（なければデフォルト値）"""
    return (
        str(attrs.get("room", "unknown")),
        str(attrs.get("shelf", "unknown")),
        str(attrs.get("device", "unknown")),
        str(attrs.get("name", "unknown")),
        str(attrs.get("parent_id", "none")),
    )


def _apply_metrics(device_id: str) -> None:
    """デバイスの現在状態をメトリクスに反映する"""
    rec = _devices.get(device_id)
    if rec is None:
        return

    room, shelf, device, device_name, parent_id = _std_attr(rec["attrs"])

    DEVICE_UP.labels(device_id=device_id).set(1 if rec["up"] else 0)

    if rec["up"]:
        POWER_WATT.labels(
            room=room,
            shelf=shelf,
            device=device,
            device_name=device_name,
            device_id=device_id,
            parent_id=parent_id,
        ).set(rec["power_watts"])
    else:
        # DOWN 時は電力を 0 とみなす
        POWER_WATT.labels(
            room=room,
            shelf=shelf,
            device=device,
            device_name=device_name,
            device_id=device_id,
            parent_id=parent_id,
        ).set(0.0)


def _remove_metrics(device_id: str, attrs: dict[str, Any]) -> None:
    """デバイス削除時にメトリクスを消去する"""
    room, shelf, device, device_name, parent_id = _std_attr(attrs)
    try:
        POWER_WATT.remove(room, shelf, device, device_name, device_id, parent_id)
    except KeyError:
        pass
    try:
        DEVICE_UP.remove(device_id)
    except KeyError:
        pass


# ---------------------------------------------------------------------------
# バックグラウンドジッタータスク
# ---------------------------------------------------------------------------
JITTER_INTERVAL = int(os.getenv("JITTER_INTERVAL", "15"))  # 秒


async def _jitter_loop() -> None:
    """auto_jitter=True のデバイスの電力値を定期的にランダム変動させる"""
    while True:
        await asyncio.sleep(JITTER_INTERVAL)
        for device_id, rec in list(_devices.items()):
            if rec["up"] and rec["auto_jitter"]:
                new_watts = round(
                    random.uniform(rec["jitter_min"], rec["jitter_max"]), 2
                )
                rec["power_watts"] = new_watts
                _apply_metrics(device_id)
                logger.debug(f"Jitter: {device_id} → {new_watts}W")


# ---------------------------------------------------------------------------
# FastAPI アプリケーション
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN001
    task = asyncio.create_task(_jitter_loop())
    logger.info(f"Dummy exporter started. Jitter interval: {JITTER_INTERVAL}s")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="dummy-exporter",
    description="Grafana テスト用 擬似 SwitchBot Prometheus Exporter",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Pydantic モデル
# ---------------------------------------------------------------------------


class AddDeviceRequest(BaseModel):
    device_id: str = Field(..., description="デバイスID（一意）")
    attrs: dict[str, Any] = Field(
        default_factory=dict,
        description="デバイス属性。name/room/shelf/device/parent_id など（任意のキー追加可）",
    )
    power_watts: float = Field(default=10.0, ge=0, description="初期電力値（W）")
    auto_jitter: bool = Field(default=True, description="自動ランダム変動の有効/無効")
    jitter_min: float = Field(default=5.0, ge=0, description="ジッター最小値（W）")
    jitter_max: float = Field(default=100.0, ge=0, description="ジッター最大値（W）")


class SetPowerRequest(BaseModel):
    watts: float = Field(..., ge=0, description="設定する電力値（W）")
    auto_jitter: bool | None = Field(
        default=None, description="同時に auto_jitter を変更する場合に指定"
    )


class SetStateRequest(BaseModel):
    up: bool = Field(..., description="True: デバイスON、False: デバイスOFF")


class UpdateAttrsRequest(BaseModel):
    attrs: dict[str, Any] = Field(..., description="更新する属性（部分更新）")


# ---------------------------------------------------------------------------
# エンドポイント
# ---------------------------------------------------------------------------


@app.get("/metrics", summary="Prometheus メトリクス出力")
def get_metrics() -> Response:
    output = generate_latest(REGISTRY)
    return Response(content=output, media_type=CONTENT_TYPE_LATEST)


@app.get("/devices", summary="デバイス一覧取得")
def list_devices() -> JSONResponse:
    return JSONResponse({"devices": list(_devices.values()), "count": len(_devices)})


@app.post("/devices", status_code=201, summary="デバイス追加")
def add_device(req: AddDeviceRequest) -> JSONResponse:
    """
    デバイスを追加する。

    ```bash
    curl -X POST http://localhost:9100/devices \\
      -H 'Content-Type: application/json' \\
      -d '{
        "device_id": "DUMMY001",
        "attrs": {"name": "pc_main", "room": "work", "shelf": "desk", "device": "pc"},
        "power_watts": 120.0,
        "auto_jitter": true,
        "jitter_min": 80.0,
        "jitter_max": 200.0
      }'
    ```
    """
    if req.device_id in _devices:
        raise HTTPException(
            status_code=409, detail=f"device_id '{req.device_id}' already exists"
        )

    if req.jitter_max < req.jitter_min:
        raise HTTPException(status_code=422, detail="jitter_max must be >= jitter_min")

    rec: dict[str, Any] = {
        "device_id": req.device_id,
        "power_watts": req.power_watts,
        "up": True,
        "auto_jitter": req.auto_jitter,
        "jitter_min": req.jitter_min,
        "jitter_max": req.jitter_max,
        "attrs": req.attrs,
    }
    _devices[req.device_id] = rec
    _apply_metrics(req.device_id)
    logger.info(f"Device added: {req.device_id} attrs={req.attrs}")
    return JSONResponse({"message": "created", "device": rec}, status_code=201)


@app.delete("/devices/{device_id}", summary="デバイス削除")
def delete_device(device_id: str) -> JSONResponse:
    """
    デバイスを削除しメトリクスからも除去する。

    ```bash
    curl -X DELETE http://localhost:9100/devices/DUMMY001
    ```
    """
    rec = _devices.pop(device_id, None)
    if rec is None:
        raise HTTPException(
            status_code=404, detail=f"device_id '{device_id}' not found"
        )
    _remove_metrics(device_id, rec["attrs"])
    logger.info(f"Device removed: {device_id}")
    return JSONResponse({"message": "deleted", "device_id": device_id})


@app.put("/devices/{device_id}/power", summary="電力値の設定")
def set_power(device_id: str, req: SetPowerRequest) -> JSONResponse:
    """
    デバイスの出力電力値を設定する。auto_jitter を同時に無効化することも可能。

    ```bash
    # 電力値を 250W に固定し、ジッターを止める
    curl -X PUT http://localhost:9100/devices/DUMMY001/power \\
      -H 'Content-Type: application/json' \\
      -d '{"watts": 250.0, "auto_jitter": false}'
    ```
    """
    rec = _devices.get(device_id)
    if rec is None:
        raise HTTPException(
            status_code=404, detail=f"device_id '{device_id}' not found"
        )

    rec["power_watts"] = req.watts
    if req.auto_jitter is not None:
        rec["auto_jitter"] = req.auto_jitter
    _apply_metrics(device_id)
    logger.info(f"Power set: {device_id} → {req.watts}W")
    return JSONResponse(
        {"message": "updated", "device_id": device_id, "power_watts": req.watts}
    )


@app.put("/devices/{device_id}/state", summary="デバイスの UP/DOWN 設定")
def set_state(device_id: str, req: SetStateRequest) -> JSONResponse:
    """
    デバイスの UP/DOWN を切り替える。DOWN にすると電力値が 0 になる。

    ```bash
    # デバイスを DOWN にする
    curl -X PUT http://localhost:9100/devices/DUMMY001/state \\
      -H 'Content-Type: application/json' \\
      -d '{"up": false}'
    ```
    """
    rec = _devices.get(device_id)
    if rec is None:
        raise HTTPException(
            status_code=404, detail=f"device_id '{device_id}' not found"
        )

    rec["up"] = req.up
    _apply_metrics(device_id)
    state_str = "UP" if req.up else "DOWN"
    logger.info(f"State set: {device_id} → {state_str}")
    return JSONResponse({"message": "updated", "device_id": device_id, "up": req.up})


@app.patch("/devices/{device_id}/attrs", summary="デバイス属性の編集")
def update_attrs(device_id: str, req: UpdateAttrsRequest) -> JSONResponse:
    """
    デバイスの属性情報を部分更新する。
    Prometheus ラベルに関わる属性（room/shelf/device/name/parent_id）を変更した場合、
    旧ラベルのメトリクスは削除され新しいラベルで再作成される。

    ```bash
    curl -X PATCH http://localhost:9100/devices/DUMMY001/attrs \\
      -H 'Content-Type: application/json' \\
      -d '{"room": "bedroom", "custom_tag": "server-a"}'
    ```
    """
    rec = _devices.get(device_id)
    if rec is None:
        raise HTTPException(
            status_code=404, detail=f"device_id '{device_id}' not found"
        )

    # 旧ラベルのメトリクスを削除してから属性を更新
    _remove_metrics(device_id, rec["attrs"])
    rec["attrs"].update(req.attrs)
    _apply_metrics(device_id)
    logger.info(f"Attrs updated: {device_id} → {rec['attrs']}")
    return JSONResponse(
        {"message": "updated", "device_id": device_id, "attrs": rec["attrs"]}
    )


# ---------------------------------------------------------------------------
# ヘルスチェック
# ---------------------------------------------------------------------------


@app.get("/healthz", summary="ヘルスチェック")
def healthz() -> JSONResponse:
    return JSONResponse({"status": "ok", "device_count": len(_devices)})


# ---------------------------------------------------------------------------
# エントリーポイント
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("METRICS_PORT", "9100"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
