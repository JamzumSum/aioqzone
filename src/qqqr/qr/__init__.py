import asyncio
import logging
import re
import typing as t
from dataclasses import dataclass
from random import random

from yarl import URL

import qqqr.message as MT
from qqqr.base import LoginBase, LoginSession
from qqqr.constant import StatusCode
from qqqr.exception import UserBreak, UserTimeout
from qqqr.qr.type import FetchDevUinResp, PollResp, PushQrResp, RedirectCookies
from qqqr.utils.encrypt import hash33
from qqqr.utils.jsjson import json_loads
from qqqr.utils.net import get_all_cookie

log = logging.getLogger(__name__)

SHOW_QR = "https://ssl.ptlogin2.qq.com/ptqrshow"
POLL_QR = "https://ssl.ptlogin2.qq.com/ptqrlogin"
LOGIN_URL = "https://ptlogin2.qzone.qq.com/check_sig"
RECENT_UIN_URL = "https://ssl.ptlogin2.qq.com/pt_fetch_dev_uin"

PTLOGIN2 = URL("https://ptlogin2.qq.com")


@dataclass(unsafe_hash=True)
class QR:
    """Class :class:`QR` represents a QR code."""

    png: t.Optional[bytes]
    """QR code content. If None, the QR is pushed to user's client."""
    sig: str
    expired: bool = False
    """Whether the QR code is expired."""

    @property
    def pushed(self):
        """Whether the QR code is pushed to user's client."""
        return self.png is None


class QrSession(LoginSession):
    def __init__(
        self,
        first_qr: QR,
        login_sig: str,
        *,
        create_time: t.Optional[float] = None,
        refresh_times: int = 0,
    ) -> None:
        super().__init__(login_sig=login_sig, create_time=create_time)
        self.refreshed = refresh_times
        """QR code refresh times counter."""
        self.current_qr = first_qr
        """A :class:`QrSession` keeps a :class:`QR` object as current QR code."""

    def new_qr(self, qr: QR):
        """Add a new QR code to this session."""
        self.current_qr.expired = True
        self.current_qr = qr
        self.refreshed += 1


class _QrHookMixin:
    def __init__(self, *args, **kwds) -> None:
        super().__init__(*args, **kwds)
        self.qr_fetched = MT.qr_fetched.with_timeout(60)
        """This emitter is triggered when a QR code is fetched."""
        self.qr_cancelled = MT.qr_cancelled()
        """This emitter is triggered when QR login is cancelled."""
        self.cancel = asyncio.Event()
        """Async-event indicating whether the loop should cancel the QR login."""
        self.refresh = asyncio.Event()
        """Async-event indicating whether the loop should refresh the QR code immediately."""


class QrLogin(LoginBase[QrSession], _QrHookMixin):
    async def new(self, no_push=False) -> QrSession:
        """Create a :class:`QrSession`. This method will:

        1. GET ``xlogin`` url to get ``pt_login_sig`` cookie;

        #. Try "quick login" (the QR code is pushed to user's client);

        #. Whether the QR code is pushed or not, a :class:`QR` object is created
           and is hold by the returned :class:`QrSession`.

        :param no_push: Do not try to push the QR code to user's client.
        :return: a :class:`QrSession`

        .. versionchanged:: 1.8.3

            Added :obj:`no_push` param.
        """
        login_sig = await self._pt_login_sig()
        if no_push:
            return QrSession(await self.show(), login_sig=login_sig)

        cookie = self.client.cookie_jar.filter_cookies(PTLOGIN2).get("pt_guid_sig")
        push_qr = False
        if cookie is None or not cookie.value:
            log.debug("pt_guid_sig not found, skip pt_fetch_dev_uin")
        else:
            params = dict(r=random(), pt_guid_token=hash33(cookie.value))
            async with self.client.get(RECENT_UIN_URL, params=params) as response:
                dev_mid_sig = response.cookies.get("dev_mid_sig")
                m = re.search(r"ptui_fetch_dev_uin_CB\((.*)\)", r := await response.text())
            log.debug("pt_fetch_dev_uin response:", r)

            if m:
                r = FetchDevUinResp.model_validate_json(m.group(1))
                push_qr = r.code == 22028 and dev_mid_sig is not None and self.uin in r.uin_list

        return QrSession(await self.show(push_qr), login_sig=login_sig)

    async def show(self, push_qr=False) -> QR:
        """This method will call ``ptqrshow`` api and wrap the response QR bytes into :class:`QR`.

        :param push_qr: push QR to mobile client.
        :return: a :class:`QR` object.
        """
        data = {
            "appid": self.app.appid,
            "daid": self.app.daid,
            "pt_3rd_aid": 0,
            "t": random(),
            "u1": self.proxy.s_url,
        }
        if push_qr:
            data.update(qr_push_uin=self.uin, type=1, qr_push=1, ptlang=2052)
        else:
            data.update(e=2, l="M", s=3, d=72, v=4)
        async with self.client.get(SHOW_QR, params=data) as r:
            qrsig = r.cookies.get("qrsig")
            if not push_qr:
                assert qrsig
                return QR(
                    png=await r.content.read(),
                    sig=qrsig.value,
                )
            m = re.search(r"ptui_qrcode_CB\((.*)\)", r := await r.text())

        log.debug("ptqrshow(qr_push) response:", r)
        assert m
        resp = PushQrResp.model_validate_json(m.group(1))
        if qrsig and resp.code == 0:
            log.info("二维码已推送至用户手机端")
            return QR(None, qrsig.value)

        log.warning(resp.message)
        cookie = self.client.cookie_jar.filter_cookies(PTLOGIN2).get("pt_guid_sig")
        if cookie:
            cookie.set(cookie.key, "", "")
        return await self.show(push_qr=False)

    async def poll(self, sess: QrSession) -> PollResp:
        """Poll QR status.

        :raise `aiohttp.ClientResponseError`: if response status code != 200

        :return: a poll response object
        """
        const = {
            "h": 1,
            "t": 1,
            "g": 1,
            "from_ui": 1,
            "ptredirect": 0,
            "ptlang": 2052,
            "js_type": 1,
            "pt_uistyle": 40,
            "has_onekey": 1,
        }
        data = {
            "u1": self.proxy.s_url,
            "ptqrtoken": hash33(sess.current_qr.sig),
            "login_sig": sess.login_sig,
            "aid": self.app.appid,
            "daid": self.app.daid,
            "o1vId": await self.deviceId(),
        }

        async with self.client.get(POLL_QR, params=data.update(const) or data) as r:
            r.raise_for_status()
            rl = re.findall(r"'(.*?)'[,\)]", await r.text())

            resp = PollResp.model_validate(
                dict(zip(["code", "", "url", "", "msg", "nickname"], rl))
            )
            log.debug(resp)
            if resp.code == StatusCode.Authenticated:
                resp.cookies = RedirectCookies.model_validate(get_all_cookie(r))
        return resp

    async def login(
        self,
        *,
        refresh_times: int = 6,
        poll_freq: float = 3,
        no_push=False,
    ):
        """Loop until cookie is returned or max :obj:`refresh_times` exceeds.

        - This method will emit :obj:`.qr_fetched` event if a new qrcode is fetched.

        - If the QR code is not scanned after :obj:`refresh_times`,
          it will raise :exc:`~qqqr.exception.UserTimeout`.

        - If :obj:`.refresh` is set, it will refresh qrcode at once without increasing expire counter.

        - If :obj:`.cancel` is set, it will raise :exc:`~qqqr.exception.UserBreak` before next polling.

        :meta public:
        :param refresh_times: max qr expire times.
        :param poll_freq: interval between two status polling, in seconds, default as 3.
        :param no_push: Do not try to push the QR code to user's client.

        :raise `UserTimeout`: if the QR code is not scanned after :obj:`refresh_times` expires.
        :raise `UserBreak`: if :obj:`.cancel` is set.

        .. versionchanged:: 1.8.3

            Added :obj:`no_push` param.
        """
        self.refresh.clear()
        self.cancel.clear()

        cnt_expire = 0
        renew = False
        sess = await self.new(no_push)

        while cnt_expire < refresh_times:
            # BUG: should we wrap hook errors here?
            await self.qr_fetched.emit_suppress_timeout(
                png=sess.current_qr.png, times=cnt_expire, qr_renew=renew
            )
            renew = False

            while not self.refresh.is_set():
                if self.cancel.is_set():
                    await self.qr_cancelled.emit()
                    raise UserBreak

                await asyncio.sleep(poll_freq)
                stat = await self.poll(sess)
                if stat.code == StatusCode.Expired:
                    sess.current_qr.expired = True
                    cnt_expire += 1
                    break
                elif stat.code == StatusCode.Authenticated:
                    sess.login_url = str(stat.url)
                    return await self._get_login_url(
                        sess,
                        cur_cookies=stat.cookies and stat.cookies.model_dump(),
                    )
            else:
                self.refresh.clear()
                renew = True

            sess.new_qr(await self.show())

        raise UserTimeout("qrscan")
