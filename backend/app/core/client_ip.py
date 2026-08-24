from functools import lru_cache
from ipaddress import ip_address, ip_network

from fastapi import Request

from app.core.config import get_settings


@lru_cache
def trusted_proxy_networks():
    return tuple(
        ip_network(value.strip())
        for value in get_settings().trusted_proxy_cidrs.split(",")
        if value.strip()
    )


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    try:
        trusted = any(ip_address(peer) in network for network in trusted_proxy_networks())
    except ValueError:
        trusted = False
    if trusted:
        forwarded = request.headers.get("x-real-ip", "").strip()
        try:
            if forwarded:
                return str(ip_address(forwarded))
        except ValueError:
            pass
    return peer
