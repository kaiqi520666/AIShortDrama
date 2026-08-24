from starlette.requests import Request

from app.core.client_ip import client_ip


def request(peer: str, real_ip: str | None = None) -> Request:
    headers = [] if real_ip is None else [(b"x-real-ip", real_ip.encode())]
    return Request({"type": "http", "client": (peer, 1234), "headers": headers})


def test_client_ip_accepts_header_only_from_trusted_proxy():
    assert client_ip(request("172.18.0.3", "203.0.113.8")) == "203.0.113.8"
    assert client_ip(request("198.51.100.4", "203.0.113.8")) == "198.51.100.4"
    assert client_ip(request("172.18.0.3", "not-an-ip")) == "172.18.0.3"
