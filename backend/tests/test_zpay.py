from app.providers.zpay import format_amount, parse_amount_cents, sign_params, verify_signature


def test_zpay_amount_conversion_and_signature():
    assert format_amount(3500) == "35.00"
    assert parse_amount_cents("35.00") == 3500
    assert parse_amount_cents("invalid") is None

    params = {
        "pid": "merchant-1",
        "money": "35.00",
        "sign_type": "MD5",
        "empty": "",
    }
    params["sign"] = sign_params(params, "secret")
    assert verify_signature(params, "secret")
    assert not verify_signature({**params, "money": "36.00"}, "secret")
