import typing as t
from ipaddress import IPv4Address

from pydantic import AnyUrl, Field, SecretStr
from pydantic_settings import BaseSettings


class LoginConfig(BaseSettings):
    uin: int = 0
    """Login uin (qq)."""


class UpLoginConfig(LoginConfig):
    pwd: SecretStr = Field(default="")
    """User password."""

    fake_ip: t.Optional[IPv4Address] = None
    """Fake IP used when collecting network environment.

    .. versionadded:: 1.8.2
    """


class QrLoginConfig(LoginConfig):
    max_refresh_times: int = 6
    """Maximum QR code refresh times."""
    poll_freq: float = 3
    """QR status polling interval."""
    no_push: bool = False
    """Do not try to push the QR code to user's client."""
