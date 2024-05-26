import asyncio
import logging
import re
import typing as t
from contextlib import suppress
from random import choice, random
from time import time_ns

from tenacity import RetryError

import qqqr.message as MT
from qqqr.base import LoginBase, LoginSession
from qqqr.constant import StatusCode
from qqqr.exception import TencentLoginError
from qqqr.type import APPID, PT_QR_APP, Proxy
from qqqr.utils.iter import firstn
from qqqr.utils.net import ClientAdapter, get_all_cookie

from ._model import CheckResp, LoginResp, RedirectCookies, VerifyResp
from .captcha import Captcha
from .encrypt import PasswdEncoder, TeaEncoder

CHECK_URL = "https://ssl.ptlogin2.qq.com/check"
LOGIN_URL = "https://ssl.ptlogin2.qq.com/login"
log = logging.getLogger(__name__)


class UpWebSession(LoginSession):
    pt_ev_token = ""

    def __init__(
        self,
        login_sig: str,
        *,
        create_time: t.Optional[float] = None,
    ) -> None:
        super().__init__(login_sig=login_sig, create_time=create_time)
        self.verify_rst: t.Optional[VerifyResp] = None
        self.sms_ticket = ""
        self.sms_code: t.Optional[str] = None
        self.login_history: t.List[LoginResp] = []

    def set_check_result(self, check: CheckResp):
        self.check_rst = check

    @property
    def pastcode(self) -> int:
        if self.login_history:
            return self.login_history[-1].code
        return 0

    @property
    def sid(self) -> str:
        return self.check_rst.session

    @property
    def code(self):
        if self.verify_rst:
            return self.verify_rst.code
        return self.check_rst.code

    @property
    def verifycode(self):
        if self.verify_rst:
            return self.verify_rst.verifycode
        return self.check_rst.verifycode

    @property
    def verifysession(self):
        if self.verify_rst:
            return self.verify_rst.ticket
        return self.check_rst.verifysession

    async def pass_vc(self, solver: "Captcha") -> None:
        """
        The `pass_vc` function is used to pass the verification tcaptcha.
        It is called when :meth:`.try_login` returns a :obj:`StatusCode.NeedCaptcha` code.

        :param solver: the :class:`Captcha` object
        :raise NotImplementedError: if cannot solve this captcha
        :raise TencentLoginError: if failed to pass captcha
        """
        try:
            self.verify_rst = await solver.verify(self.sid)
        except RetryError as e:
            from qqqr.constant import captcha_status_description

            r: VerifyResp = e.last_attempt.result()
            raise TencentLoginError(
                StatusCode.NeedCaptcha,
                captcha_status_description.get(r.code, r.errMessage),
                subcode=r.code,
            ) from e.last_attempt.exception()

        log.info("成功通过验证码")


class _UpHookMixin:
    def __init__(self, *args, **kwds) -> None:
        super().__init__(*args, **kwds)
        self.sms_code_input = MT.sms_code_input.with_timeout(60)
        """This emitter is triggered when SMS verify code is needed during login."""


class UpWebLogin(LoginBase[UpWebSession], _UpHookMixin):
    """
    .. versionchanged:: 0.13.0.dev1

        :class:`~qqqr.up.encrypt.TeaEncoder` is the unique :class:`~qqqr.up.encrypt.PasswdEncoder`.
        ``NodeEncoder`` is removed.
    """

    def __init__(
        self,
        client: ClientAdapter,
        uin: int,
        pwd: str,
        h5=True,
        app: t.Optional[APPID] = None,
        proxy: t.Optional[Proxy] = None,
        info: t.Optional[PT_QR_APP] = None,
        fake_ip: t.Optional[str] = None,
    ):
        super().__init__(client, uin=uin, h5=h5, app=app, proxy=proxy, info=info)
        self.pwd = pwd
        self.pwder = TeaEncoder(pwd)
        self.captcha = Captcha(
            self.client, self.app.appid, str(self.login_page_url), fake_ip=fake_ip
        )

    async def new(self) -> UpWebSession:
        """Create a :class:`UpWebSession`. This will trigger a GET to ``xlogin`` url.

        :raise `aiohttp.ClientResponseError`: if response status != 200

        :return: a up login session
        """
        return UpWebSession(await self._pt_login_sig())

    async def check(self, sess: UpWebSession):
        """This will call ``check`` api of Qzone, and receive result about
        whether this login needs a captcha, sms verification, etc.

        :param sess: Session got from :meth:`~UpWebLogin.new`.
        """
        data = {
            "regmaster": "",
            "pt_tea": 2,
            "pt_vcode": 1,
            "uin": self.uin,
            "appid": self.app.appid,
            # 'js_ver': 21072114,
            "js_type": 1,
            "login_sig": sess.login_sig,
            "u1": self.proxy.s_url,
            "r": random(),
            "pt_uistyle": 40,
        }
        async with self.client.get(CHECK_URL, params=data) as r:
            r.raise_for_status()
            rl = re.findall(r"'(.*?)'[,\)]", await r.text())

        rdict = dict(
            zip(
                ["code", "verifycode", "salt", "verifysession", "isRandSalt", "ptdrvs", "session"],
                rl,
            )
        )
        sess.set_check_result(CheckResp.model_validate(rdict))

    async def send_sms_code(self, sess: UpWebSession):
        """Send verify sms (to get dynamic code)

        :param sess: The up login session to send sms code
        """
        data = {
            "bkn": "",
            "uin": self.uin,
            "aid": self.app.appid,
            "pt_sms_ticket": sess.sms_ticket,
        }
        async with self.client.get(
            "https://ui.ptlogin2.qq.com/ssl/send_sms_code", params=data
        ) as r:
            rl = re.findall(r"'(.*?)'[,\)]", await r.text())
        # ptui_sendSMS_CB('10012', '短信发送成功！')
        if int(rl[0]) != 10012:
            raise TencentLoginError(sess.pastcode, rl[1])

    async def _make_login_param(self, sess: UpWebSession):
        const = {
            "h": 1,
            "t": 1,
            "g": 1,
            "ptredirect": 0,
            "from_ui": 1,
            "ptlang": 2052,
            "js_type": 1,
            "pt_uistyle": 40,
        }
        data = {
            "u": self.uin,
            "p": await self.pwder.encode(sess.check_rst.salt, sess.verifycode),
            "verifycode": sess.verifycode,
            "pt_vcode_v1": int(sess.verify_rst is not None),
            "pt_verifysession_v1": sess.verifysession,
            "pt_randsalt": sess.check_rst.isRandSalt,
            "u1": self.proxy.s_url,
            "login_sig": sess.login_sig,
            "aid": self.app.appid,
            "daid": self.app.daid,
            "action": f"{3 if sess.verify_rst is not None else 2}-{choice([1, 2])}-{int(time_ns() / 1e6)}",
            "ptdrvs": sess.check_rst.ptdrvs,
            "sid": sess.check_rst.session,
            "o1vId": await self.deviceId(),
        }
        data.update(const)
        return data

    async def try_login(self, sess: UpWebSession) -> LoginResp:
        """
        Check if current session meets the login condition.
        It takes a session object and returns response of this try.

        :param sess: Store the session information
        :return: A login response
        """
        async with self.client.get(
            LOGIN_URL, params=await self._make_login_param(sess)
        ) as response:
            response.raise_for_status()
            rl = re.findall(r"'(.*?)'[,\)]", await response.text())
            resp = LoginResp.model_validate(
                dict(zip(["code", "", "url", "", "msg", "nickname", "pt_ev_token"], rl))
            )
            log.debug(resp)

            if resp.code == StatusCode.NeedSmsVerify:
                sess.sms_ticket = ""
                if m := response.cookies.get("pt_sms_ticket"):
                    sess.sms_ticket = m.value
            elif resp.code == StatusCode.Authenticated:
                cookies = get_all_cookie(response)
                if "pt_guid_sig" not in cookies:
                    # TODO: patch for h5 up login
                    cookies["pt_guid_sig"] = ""
                resp.cookies = RedirectCookies.model_validate(cookies)

        return resp

    async def login(self):
        sess = await self.new()
        await self.check(sess)

        if sess.code == StatusCode.NeedCaptcha:
            log.warning("需通过防水墙")

            try:
                await sess.pass_vc(self.captcha)
            except NotImplementedError:
                raise TencentLoginError(StatusCode.NeedCaptcha, "未能识别验证码")
            if sess.verify_rst is None or not sess.verify_rst.ticket:
                raise TencentLoginError(StatusCode.NeedCaptcha, "验证过程出现错误")

        while True:
            resp = await self.try_login(sess)
            pastcode = sess.pastcode
            sess.login_history.append(resp)
            if resp.code == StatusCode.Authenticated:
                sess.login_url = str(resp.url)
                return await self._get_login_url(
                    sess,
                    cur_cookies=resp.cookies and resp.cookies.model_dump(),
                )
            elif resp.code == StatusCode.NeedSmsVerify:
                log.warning("需用户短信验证")
                if pastcode == StatusCode.NeedSmsVerify:
                    raise TencentLoginError(resp.code, "重复要求动态验证码")
                if not self.sms_code_input.has_impl:
                    # fast return so we won't always request smscode which may risk test account.
                    raise TencentLoginError(resp.code, "未实现的功能：输入验证码")
                await self.send_sms_code(sess)
                with suppress(BaseException):
                    hook_results = await self.sms_code_input.results(
                        uin=self.uin, phone=resp.msg, nickname=resp.nickname
                    )
                    sess.sms_code = firstn(hook_results, lambda c: c and len(c.strip()) >= 4)
                if sess.sms_code is None:
                    raise TencentLoginError(resp.code, "未获得动态(SMS)验证码")
            else:
                raise TencentLoginError(resp.code, resp.msg)
