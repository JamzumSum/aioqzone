import asyncio
import base64
import json
import re
from math import floor
from random import random
from time import time
from typing import Dict, List, Type, TypeVar, cast

from httpx import URL

from jssupport.execjs import ExecJS, Partial
from jssupport.jsjson import json_loads

from ...utils.daug import du
from ...utils.iter import first
from ...utils.net import ClientAdapter
from ..type import CaptchaData, PrehandleResp, VerifyResp
from .jigsaw import Jigsaw, imitate_drag
from .vm import TDC, MatchMd5

PREHANDLE_URL = "https://t.captcha.qq.com/cap_union_prehandle"
SHOW_NEW_URL = "https://t.captcha.qq.com/cap_union_new_show"
VERIFY_URL = "https://t.captcha.qq.com/cap_union_new_verify"

time_s = lambda: int(1e3 * time())
rnd6 = lambda: str(random())[2:8]

_TDC_TY = TypeVar("_TDC_TY", bound=TDC)


def hex_add(h: str, o: int):
    if h.endswith("#"):
        return h + str(o)
    if not h:
        return o
    return hex(int(h, 16) + o)[2:]


class TcaptchaSession:
    def __init__(
        self,
        prehandle: PrehandleResp,
    ) -> None:
        self.prehandle = prehandle

        self.set_captcha()

    def set_captcha(self):
        self.conf = self.prehandle.captcha
        self.cdn_urls = (
            self._cdn(self.conf.render.bg.img_url),
            self._cdn(self.conf.render.sprite_url),
        )
        self.cdn_imgs: List[bytes] = []
        self.piece_sprite = first(self.conf.render.sprites, lambda s: s.move_cfg)

    def set_js_env(self, tdc: TDC):
        self.tdc = tdc

    def set_pow_answer(self, ans: int, duration: int):
        self.pow_ans = ans
        self.duration = duration

    def set_captcha_answer(self, left: int, top: int):
        self.jig_ans = left, top

    def _cdn(self, rel_path: str) -> URL:
        return URL("https://t.captcha.qq.com").join(rel_path)

    def tdx_js_url(self):
        assert self.conf
        return URL("https://t.captcha.qq.com").join(self.conf.common.tdc_path)

    def vmslide_js_url(self):
        raise NotImplementedError


class Captcha:
    # (c_login_2.js)showNewVC-->prehandle
    # prehandle(recall)--call tcapcha-frame.*.js-->new_show
    # new_show(html)--js in html->loadImg(url)
    def __init__(self, client: ClientAdapter, appid: int, sid: str, xlogin_url: str):
        self.client = client
        self.appid = appid
        self.sid = sid
        self.xlogin_url = xlogin_url
        self.client.referer = "https://xui.ptlogin2.qq.com/"
        self.__match_md5 = MatchMd5()
        """Static js environment to match md5"""

    @property
    def base64_ua(self):
        return base64.b64encode(self.client.ua.encode()).decode()

    async def new(self):
        """``prehandle``. Call this method to generate a new verify session.

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
        }
        data = {
            "aid": self.appid,
            "accver": 1,
            "ua": self.base64_ua,
            "sid": self.sid,
            "entry_url": self.xlogin_url,
            # 'js': '/tcaptcha-frame.a75be429.js'
            "subsid": 1,
            "callback": CALLBACK,
        }
        async with await self.client.get(PREHANDLE_URL, params=du(const, data)) as r:
            r.raise_for_status()
            m = re.search(CALLBACK + r"\((\{.*\})\)", r.text)

        assert m
        r = PrehandleResp.parse_raw(m.group(1))
        return TcaptchaSession(r)

    prehandle = new
    """alias of :meth:`.new`"""

    async def get_tdc_vm(self, sess: TcaptchaSession, *, cls: Type[_TDC_TY] = TDC):
        js_url = sess.tdx_js_url()
        tdc = cls("", header=self.client.headers)

        async with await self.client.get(js_url) as r:
            r.raise_for_status()
            tdc.load_vm("".join([i async for i in r.aiter_text()]))

        sess.set_js_env(tdc)

    async def match_md5(self, sess: TcaptchaSession):
        pow_cfg = sess.conf.common.pow_cfg
        ans, dur = await self.__match_md5(pow_cfg.prefix, pow_cfg.md5)
        sess.set_pow_answer(ans, dur)

    async def get_captcha_problem(self, sess: TcaptchaSession):
        async def r(url):
            async with await self.client.get(url) as r:
                r.raise_for_status()
                return b"".join([i async for i in r.aiter_bytes()])

        for i in await asyncio.gather(*(r(i) for i in sess.cdn_urls)):
            sess.cdn_imgs.append(i)

    async def solve_captcha(self, sess: TcaptchaSession):
        if not sess.cdn_imgs:
            await self.get_captcha_problem(sess)
        assert sess.cdn_imgs

        piece_pos = tuple(
            slice(
                sess.piece_sprite.sprite_pos[i],
                sess.piece_sprite.sprite_pos[i] + sess.piece_sprite.size_2d[i],
            )
            for i in range(2)
        )

        jig = Jigsaw(*sess.cdn_imgs, piece_pos=piece_pos, top=sess.piece_sprite.init_pos[1])
        sess.set_captcha_answer(jig.left, jig.top)

        sess.tdc.set_data(clientType=2)
        sess.tdc.set_data(coordinate=[10, 24, 0.4103])
        sess.tdc.set_data(
            trycnt=1,
            refreshcnt=0,
            slideValue=imitate_drag(floor(jig.left * jig.rate)),
            dragobj=1,
        )
        sess.tdc.set_data(ft="qf_7P_n_H")

    async def verify(self):
        sess = await self.new()
        await self.get_tdc_vm(sess)

        waitEnd = time() + 0.6 * random() + 0.9

        await self.match_md5(sess)
        await self.get_captcha_problem(sess)
        await self.solve_captcha(sess)

        collect = await sess.tdc.get_data()
        tlg = len(collect)

        ans = dict(
            elem_id=1,
            type=sess.piece_sprite.move_cfg.data_type[0],  # type: ignore
            data="{0},{1}".format(*sess.jig_ans),
        )
        data = {
            "collect": collect,
            "tlg": tlg,
            "eks": (await sess.tdc.get_info())["info"],
            "sess": sess.prehandle.sess,
            "ans": json.dumps(ans),
            "pow_answer": hex_add(sess.conf.common.pow_cfg.prefix, sess.pow_ans),
            "pow_calc_time": sess.duration,
        }
        await asyncio.sleep(max(0, waitEnd - time()))
        async with await self.client.post(VERIFY_URL, data=data) as r:
            r = VerifyResp.parse_raw(r.text)

        if r.code:
            raise RuntimeError(f"Code {r.code}: {r.errMessage}")
        return r
