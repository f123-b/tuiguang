"""Bounded direct HTTPS with a pinned, public DNS result and original TLS name."""

import http.client
import ipaddress
import socket
import ssl
from urllib.parse import quote, urlsplit

from .errors import DomainError

LIMIT = 512 * 1024


def validate_url(url):
    try:
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.port not in (None, 443)
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or any(ord(c) < 32 for c in url)
        ):
            raise ValueError("invalid URL")
        host = parts.hostname.encode("idna").decode("ascii").lower()
        if host == "localhost" or "." not in host or host.endswith((".local", ".internal", ".localhost")):
            raise ValueError("local name")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address and not address.is_global:
            raise ValueError("nonpublic literal")
        return parts, host
    except (ValueError, UnicodeError):
        raise DomainError(
            "SOURCE_ADDRESS_DENIED", "来源须为无账号、查询参数和片段的公网 HTTPS 地址", 422
        ) from None


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, hostname, address):
        super().__init__(hostname, timeout=12, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        raw = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def fetch(url):
    parts, host = validate_url(url)
    try:
        addresses = {row[4][0] for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
            raise DomainError("SOURCE_ADDRESS_DENIED", "来源地址解析到非公网目标，未访问", 422)
        address = sorted(addresses, key=lambda a: (":" in a, a))[0]
        path = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
        connection = PinnedHTTPS(host, address)
        try:
            connection.request(
                "GET",
                path,
                headers={
                    "Host": host,
                    "User-Agent": "XuliuLocalCreator/0.11",
                    "Accept": "text/plain,text/html,application/json",
                    "Accept-Encoding": "identity",
                },
            )
            response = connection.getresponse()
            if response.status != 200:
                raise DomainError(
                    "SOURCE_FETCH_FAILED", f"来源返回 HTTP {response.status}，未跟随跳转或覆盖旧快照", 422
                )
            content_type = response.getheader("Content-Type", "").split(";", 1)[0].lower()
            if (
                not (
                    content_type.startswith("text/")
                    or content_type in ("application/json", "application/octet-stream")
                )
                or response.getheader("Content-Encoding", "identity") != "identity"
            ):
                raise DomainError(
                    "SOURCE_FORMAT_UNSUPPORTED", "来源须为未压缩的文本、HTML、Markdown 或 JSON", 422
                )
            data = response.read(LIMIT + 1)
            if len(data) > LIMIT:
                raise DomainError("SOURCE_TOO_LARGE", "来源超过 512 KiB，请缩小文档或上传版本摘要", 422)
            return data.decode("utf-8-sig"), content_type
        finally:
            connection.close()
    except (OSError, ValueError, UnicodeError, http.client.HTTPException):
        raise DomainError("SOURCE_FETCH_FAILED", "来源连接或 UTF-8 解码失败，保留上次快照", 422) from None
