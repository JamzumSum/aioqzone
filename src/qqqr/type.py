import sys
from dataclasses import dataclass

from pydantic import BaseModel

if sys.version_info >= (3, 10):
    frozen_args = dict(frozen=True, slots=True)
else:
    frozen_args = dict(frozen=True)


@dataclass(**frozen_args)
class PT_QR_APP:
    app: str = ""
    link: str = ""
    register: str = ""
    help: str = ""


@dataclass(**frozen_args)
class Proxy:
    s_url: str
    proxy_url: str = ""


@dataclass(**frozen_args)
class APPID:
    appid: int
    daid: int


class RedirectCookies(BaseModel):
    supertoken: str
    superkey: str
    pt_guid_sig: str
    pt_recent_uins: str = ""
    ptcz: str
