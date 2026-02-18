import pytest
import respx
from httpx import Response
from src.main import fetch_device_status, POWER_WATT


@pytest.mark.asyncio
@respx.mock
async def test_fetch_device_status_success(client):
    # 1. SwitchBot APIのレスポンスを偽装
    device_id = "v2E12345"
    respx.get(f"https://api.switch-bot.com/v1.1/devices/{device_id}/status").mock(
        return_value=Response(
            200,
            json={
                "statusCode": 100,
                "body": {"weight": 125.5},  # 電力値
                "message": "success",
            },
        )
    )

    device = {
        "id": device_id,
        "name": "Server",
        "house": "Home",
        "room": "Work",
        "shelf": "Rack1",
    }

    # 2. 実行
    await fetch_device_status(client, device, "token", "secret")

    # 3. 検証：PrometheusのGaugeに正しい値セットされたか
    # labelsの順序は定義順
    val = POWER_WATT.labels(
        house="Home",
        room="Work",
        shelf="Rack1",
        device_name="Server",
        device_id=device_id,
    ).get()

    assert val == 125.5
