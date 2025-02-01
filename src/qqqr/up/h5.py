import logging
import re
from random import random

from yarl import URL

from ._model import CheckRespValidator
from .web import UpWebLogin, UpWebSession

log = logging.getLogger(__name__)

CHECK_URL = "https://ui.ptlogin2.qq.com/ssl/check"
LOGIN_URL = "https://ui.ptlogin2.qq.com/ssl/login"


class UpH5Login(UpWebLogin):
    @property
    def login_page_url(self):
        params = dict(
            pt_hide_ad=1,
            style=9,
            appid=self.app.appid,
            pt_no_auth=1,
            pt_wxtest=1,
            daid=self.app.daid,
            s_url=self.proxy.s_url,
        )
        return URL("https://ui.ptlogin2.qq.com/cgi-bin/login").with_query(params)

    async def check(self, sess: UpWebSession):
        data = dict(
            pt_tea=2,
            uin=self.uin,
            appid=self.app.appid,
            daid=self.app.daid,
            ptlang=2052,
            regmaster="",
            pt_uistyle=9,
            o1vId=await self.deviceId(),
            r=random(),
        )
        async with self.client.get(CHECK_URL, params=data) as r:
            r.raise_for_status()
            rl = re.findall(r"'(.*?)'[,\)]", await r.text())

        sess.set_check_result(CheckRespValidator.validate_python(rl))

    async def _make_login_param(self, sess: UpWebSession):
        const = {
            "regmaster": "",
            "h": 1,
            "g": 1,
            "ptredirect": 1,
            "from_ui": 1,
            "ptlang": 2052,
            "pt_uistyle": 9,
            "fp": "loginerroralert",
            "low_login_enable": 0,
            "device": 2,
            "pt_3rd_aid": 0,
        }
        data = {
            "u": self.uin,
            "p": await self.pwder.encode(sess.check_rst.salt, sess.verifycode),
            "verifycode": sess.verifycode,
            "pt_vcode_v1": int(sess.verify_rst is not None),
            "pt_verifysession_v1": sess.verifysession,
            "pt_randsalt": sess.check_rst.isRandSalt,
            "u1": self.proxy.s_url,
            "aid": self.app.appid,
            "daid": self.app.daid,
            "ptdrvs": sess.check_rst.ptdrvs,
            "sid": sess.check_rst.session,
            # "pt_ev_token": sess.pt_ev_token,
            "o1vId": await self.deviceId(),
        }
        data.update(const)
        return data
