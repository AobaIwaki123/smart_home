import pytest
import respx
from httpx import Response, TimeoutException, HTTPError
from src.main import fetch_device_status, POWER_WATT, DEVICE_UP, API_REMAINING


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
    )._value.get()

    assert val == 125.5


@pytest.mark.asyncio
@respx.mock
async def test_fetch_device_status_api_error_500(client):
    """APIが500エラーを返す場合のテスト"""
    device_id = "v2E12345"
    respx.get(f"https://api.switch-bot.com/v1.1/devices/{device_id}/status").mock(
        return_value=Response(500, json={"error": "Internal Server Error"})
    )

    device = {
        "id": device_id,
        "name": "Server",
        "house": "Home",
        "room": "Work",
        "shelf": "Rack1",
    }

    # 実行（エラーが発生するはず）
    await fetch_device_status(client, device, "token", "secret")

    # デバイス状態がダウンにセットされているか確認
    device_status = DEVICE_UP.labels(device_id=device_id)._value.get()
    assert device_status == 0, "APIエラー時はデバイスをダウン状態にする必要があります"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_device_status_missing_weight_field(client):
    """weightフィールドが欠落している場合のテスト"""
    device_id = "v2E12345"
    respx.get(f"https://api.switch-bot.com/v1.1/devices/{device_id}/status").mock(
        return_value=Response(
            200,
            json={
                "statusCode": 100,
                "body": {},  # weightフィールドなし
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

    # 実行
    await fetch_device_status(client, device, "token", "secret")

    # デフォルト値0がセットされているか確認
    val = POWER_WATT.labels(
        house="Home",
        room="Work",
        shelf="Rack1",
        device_name="Server",
        device_id=device_id,
    )._value.get()

    assert val == 0, "weightフィールドが欠落している場合は0をセットする必要があります"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_device_status_invalid_status_code(client):
    """statusCodeが100以外の場合のテスト"""
    device_id = "v2E12345"
    respx.get(f"https://api.switch-bot.com/v1.1/devices/{device_id}/status").mock(
        return_value=Response(
            200,
            json={
                "statusCode": 190,  # エラーコード
                "body": {"weight": 125.5},
                "message": "Device not found",
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

    # 実行（例外が発生するはず）
    await fetch_device_status(client, device, "token", "secret")

    # デバイス状態がダウンにセットされているか確認
    device_status = DEVICE_UP.labels(device_id=device_id)._value.get()
    assert device_status == 0, (
        "statusCodeエラー時はデバイスをダウン状態にする必要があります"
    )


@pytest.mark.asyncio
@respx.mock
async def test_fetch_device_status_timeout(client):
    """ネットワークタイムアウトが発生した場合のテスト"""
    device_id = "v2E12345"
    respx.get(f"https://api.switch-bot.com/v1.1/devices/{device_id}/status").mock(
        side_effect=TimeoutException("Request timeout")
    )

    device = {
        "id": device_id,
        "name": "Server",
        "house": "Home",
        "room": "Work",
        "shelf": "Rack1",
    }

    # 実行
    await fetch_device_status(client, device, "token", "secret")

    # デバイス状態がダウンにセットされているか確認
    device_status = DEVICE_UP.labels(device_id=device_id)._value.get()
    assert device_status == 0, (
        "タイムアウト時はデバイスをダウン状態にする必要があります"
    )


@pytest.mark.asyncio
@respx.mock
async def test_fetch_device_status_rate_limit_header(client):
    """APIレート制限ヘッダーの処理テスト"""
    device_id = "v2E12345"
    respx.get(f"https://api.switch-bot.com/v1.1/devices/{device_id}/status").mock(
        return_value=Response(
            200,
            headers={"x-ratelimit-remaining": "99"},
            json={
                "statusCode": 100,
                "body": {"weight": 100.0},
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

    # 実行
    await fetch_device_status(client, device, "token", "secret")

    # API制限カウントがセットされているか確認
    remaining_count = API_REMAINING._value.get()
    assert remaining_count == 99, "レート制限の残り回数がセットされている必要があります"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_device_status_cleans_up_stale_metrics(client):
    """エラー時に古いメトリクスが適切に削除されるかテスト"""
    device_id = "v2E12345"

    device = {
        "id": device_id,
        "name": "Server",
        "house": "Home",
        "room": "Work",
        "shelf": "Rack1",
    }

    # 1. 最初に正常なデータをセット
    respx.get(f"https://api.switch-bot.com/v1.1/devices/{device_id}/status").mock(
        return_value=Response(
            200,
            json={
                "statusCode": 100,
                "body": {"weight": 50.0},
                "message": "success",
            },
        )
    )

    await fetch_device_status(client, device, "token", "secret")

    # メトリクスがセットされていることを確認
    val = POWER_WATT.labels(
        house="Home",
        room="Work",
        shelf="Rack1",
        device_name="Server",
        device_id=device_id,
    )._value.get()
    assert val == 50.0

    # 2. 次にエラーレスポンスを設定
    respx.get(f"https://api.switch-bot.com/v1.1/devices/{device_id}/status").mock(
        return_value=Response(500, json={"error": "Server Error"})
    )

    await fetch_device_status(client, device, "token", "secret")

    # デバイス状態がダウンになっているか確認
    device_status = DEVICE_UP.labels(device_id=device_id)._value.get()
    assert device_status == 0

    # 古い電力メトリクスが削除されているか確認
    # (削除されているため、アクセスしようとすると KeyError または None が返される)
    try:
        stale_val = POWER_WATT.labels(
            house="Home",
            room="Work",
            shelf="Rack1",
            device_name="Server",
            device_id=device_id,
        )._value.get()
        # メトリクスが削除されていれば、この値は存在しないか、デフォルト値になる
        assert stale_val is None or stale_val == 0, (
            "エラー時は古いメトリクスが削除される必要があります"
        )
    except KeyError:
        # KeyErrorが発生すれば、正しく削除されている
        pass
