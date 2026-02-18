import pytest
from src.main import generate_sign


def test_generate_sign_format():
    token = "test_token"
    secret = "test_secret"

    sign, t, nonce = generate_sign(token, secret)

    # 形式チェック
    assert len(sign) > 0
    assert sign.isupper()  # 仕様書通り大文字か
    assert t.isdigit()  # タイムスタンプが数字か
    assert len(nonce) == 36  # UUID形式か
