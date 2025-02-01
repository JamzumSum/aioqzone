import asyncio
import base64
import json
import logging
import re
import typing as t
from random import random
from time import time
from urllib.parse import unquote

from pydantic import ValidationError
from tenacity import after_log, retry, retry_if_exception_type, retry_if_result, stop_after_attempt

import qqqr.message as MT
from qqqr.message import solve_select_captcha, solve_slide_captcha

from ...utils.net import ClientAdapter
from .._model import VerifyResp
from ._model import PrehandleResp, PrehandleRespValidator
from .capsess import BaseTcaptchaSession as TcaptchaSession
from .click import ClickCaptchaSession
from .select import SelectCaptchaSession

PREHANDLE_URL = "https://t.captcha.qq.com/cap_union_prehandle"
SHOW_NEW_URL = "https://t.captcha.qq.com/cap_union_new_show"
VERIFY_URL = "https://t.captcha.qq.com/cap_union_new_verify"

time_ms = lambda: int(1e3 * time())
"""+new Date"""
rnd6 = lambda: str(random())[2:8]
log = logging.getLogger(__name__)


def hex_add(h: str, o: int):
    if h.endswith("#"):
        return h + str(o)
    if not h:
        return o
    return hex(int(h, 16) + o)[2:]


class _CaptchaHookMixin:
    def __init__(self, *args, **kwds) -> None:
        super().__init__(*args, **kwds)
        self.solve_select_captcha = MT.solve_select_captcha.with_timeout(60)
        self.solve_slide_captcha = MT.solve_slide_captcha.with_timeout(60)


class Captcha(_CaptchaHookMixin):
    # (c_login_2.js)showNewVC-->prehandle
    # prehandle(recall)--call tcapcha-frame.*.js-->new_show
    # new_show(html)--js in html->loadImg(url)
    solve_select_captcha: solve_select_captcha.TyInst
    solve_slide_captcha: solve_slide_captcha.TyInst

    def __init__(
        self,
        client: ClientAdapter,
        appid: int,
        xlogin_url: str,
        fake_ip: t.Optional[str] = None,
    ):
        """
        :param client: network client
        :param appid: Specify the appid of the application
        :param xlogin_url: :obj:`LoginBase.xlogin_url`
        """

        super().__init__()
        self.client = client
        self.appid = appid
        self.xlogin_url = xlogin_url
        self.client.headers["Referer"] = "https://xui.ptlogin2.qq.com/"
        self.fake_ip = fake_ip

    @property
    def base64_ua(self):
        """
        The base64_ua function encodes the User-Agent header in base64.

        :return: A string containing the base64 encoded user agent
        """

        return base64.b64encode(self.client.headers["User-Agent"].encode()).decode()

    async def new(self, sid: str) -> TcaptchaSession:
        """``prehandle``. Call this method to generate a new verify session.

        :param sid: login session id, got from :meth:`UpWebLogin.new`
        :return: a tcaptcha session
        """
        CALLBACK = "_aq_596882"
        const = {
            "protocol": "https",
            "noheader": 1,
            "showtype": "embed",
            "enableDarkMode": 0,
            "grayscale": 1,
            "clientype": 2,
            "cap_cd": "",
            "uid": "",
            "wxLang": "",
            "lang": "zh-CN",
            "sess": "",
            "fb": 1,
            "aged": 0,
            "enableAged": 0,
            "elder_captcha": 0,
            "login_appid": "",
            "wb": 2,
        }
        data = {
            "aid": self.appid,
            "accver": 1,
            "ua": self.base64_ua,
            "sid": sid,
            "entry_url": self.xlogin_url,
            # 'js': '/tcaptcha-frame.a75be429.js'
            "subsid": 1,
            "callback": CALLBACK,
        }
        data.update(const)

        @retry(stop=stop_after_attempt(2), retry=retry_if_exception_type(ValidationError))
        async def retry_closure():
            async with self.client.get(PREHANDLE_URL, params=data) as r:
                r.raise_for_status()
                m = re.search(CALLBACK + r"\((\{.*\})\)", await r.text("utf8"))

            assert m
            return PrehandleRespValidator.validate_json(m.group(1))

        sess = TcaptchaSession.factory(sid, await retry_closure())
        if isinstance(sess, SelectCaptchaSession):
            sess.solve_captcha_hook = self.solve_select_captcha
        elif isinstance(sess, ClickCaptchaSession):
            raise NotImplementedError("“依次点击”类验证码正在施工")
        else:
            sess.solve_captcha_hook = self.solve_slide_captcha
        return sess

    prehandle = new
    """alias of :meth:`.new`"""

    @retry(
        stop=stop_after_attempt(2),
        retry=retry_if_result(lambda rst: not rst.ticket),
        after=after_log(log, logging.WARNING),
    )
    async def verify(self, sid: str, *, loop: t.Optional[asyncio.AbstractEventLoop] = None):
        """
        :raise NotImplementedError: cannot solve captcha
        """
        sess = await self.new(sid)
        loop = loop or asyncio.get_event_loop()

        async def get_solve_captcha(client: ClientAdapter) -> str:
            await sess.get_captcha_problem(client)
            return await sess.solve_captcha()

        async def get_tdc_collect(client: ClientAdapter) -> str:
            await sess.get_tdc(client, ip=self.fake_ip)
            return unquote(str(sess.tdc.getData(None, True)))

        ans, collect, _ = await asyncio.gather(
            get_solve_captcha(self.client),
            get_tdc_collect(self.client),
            loop.run_in_executor(None, sess.solve_workload),
        )
        if not ans:
            raise NotImplementedError("Failed to solve captcha")
        ans = dict(
            elem_id=1,
            type=sess.data_type,
            data=ans,
        )
        info = sess.tdc.getInfo(None)["info"]
        assert isinstance(info, str)

        data = {
            "collect": collect,
            "tlg": len(collect),
            "eks": info.strip("'"),
            "sess": sess.prehandle["sess"],
            "ans": json.dumps([ans]),
            "pow_answer": hex_add(sess.conf["common"]["pow_cfg"]["prefix"], sess.pow_ans),
            "pow_calc_time": sess.duration,
        }
        log.debug(f"verify post data: {data}")

        async with self.client.post(VERIFY_URL, data=data) as r:
            r = VerifyResp.model_validate_json(await r.text("utf8"))

        log.debug(f"verify result: {r}")
        return r
