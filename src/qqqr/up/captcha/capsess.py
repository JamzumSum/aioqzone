import asyncio
import logging
import typing as t
from abc import ABC, abstractmethod
from hashlib import md5
from time import time

from pydantic import ValidationError
from tylisten import HookSpec
from yarl import URL

from qqqr.utils.net import ClientAdapter

from ._model import CommonRender, PrehandleResp

log = logging.getLogger(__name__)


class BaseTcaptchaSession(ABC):
    data_type: str
    mouse_track: "asyncio.Future[t.Optional[t.List[t.Tuple[int, int]]]]"
    solve_captcha_hook: HookSpec

    def __init__(
        self,
        session: str,
        prehandle: PrehandleResp,
    ) -> None:
        """
        :param session: login session id, got from :meth:`UpWebLogin.new`
        """
        super().__init__()
        self.session = session
        self.prehandle = prehandle
        self.parse_captcha_data()
        self.mouse_track = asyncio.get_event_loop().create_future()

    def parse_captcha_data(self):
        assert self.prehandle["captcha"]
        self.conf = self.prehandle["captcha"]

    def solve_workload(self, *, timeout: float = 30.0):
        """
        The solve_workload function solves the workload from Tcaptcha:
        It solves md5(:obj:`PowCfg.prefix` + str(?)) == :obj:`PowCfg.md5`.
        The result and the calculating duration will be saved into this session.

        :param timeout: Calculating timeout, default as 30 seconds.
        :return: None
        """

        pow_cfg = self.conf["common"]["pow_cfg"]
        nonce = str(pow_cfg["prefix"]).encode()
        target = pow_cfg["md5"].lower()

        start = time()
        cnt = 0

        while time() - start < timeout:
            if md5(nonce + str(cnt).encode()).hexdigest() == target:
                break
            cnt += 1

        self.pow_ans = cnt
        # on some environment this time is too low... add a limit
        self.duration = max(int((time() - start) * 1e3), 50)

    def _cdn_join(self, rel_path: str) -> URL:
        return URL("https://t.captcha.qq.com").with_path(rel_path, encoded=True)

    def _tdx_js_url(self):
        assert self.conf
        return URL("https://t.captcha.qq.com").with_path(
            self.conf["common"]["tdc_path"], encoded=True
        )

    def _vmslide_js_url(self):
        raise NotImplementedError

    async def get_tdc(
        self, client: ClientAdapter, ua: t.Optional[str] = None, ip: t.Optional[str] = None
    ):
        """
        .. note:: If :obj:`.mouse_track` should be set, set it before calling this method.
        """
        from chaosvm import prepare

        async with client.get(self._tdx_js_url()) as r:
            r.raise_for_status()
            self.tdc = prepare(
                await r.text("utf8"),
                ip=ip or self.prehandle["uip"],
                ua=ua or client.headers["User-Agent"],
                mouse_track=await self.mouse_track,
            )

    @abstractmethod
    async def get_captcha_problem(self, client: ClientAdapter): ...

    @abstractmethod
    async def solve_captcha(self) -> str:
        """If failed to solve captcha, return an empty string."""
        return ""

    @classmethod
    def factory(cls, session: str, prehandle: PrehandleResp):
        assert prehandle["captcha"]

        try:
            render = CommonRender.model_validate(prehandle["captcha"]["render"])
        except ValidationError:
            log.error(prehandle["captcha"]["render"])
            raise

        if render.bg.cfg["data_type"] == "DynAnswerType_UC":
            from .select import SelectCaptchaSession as cls
        elif render.bg.cfg["data_type"] == "DynAnswerType_POS":
            log.error(prehandle["captcha"]["render"])
            raise NotImplementedError("“依次点击”类验证码正在施工")
            from .click import ClickCaptchaSession as cls
        else:
            from .slide import SlideCaptchaSession as cls

        return cls(session=session, prehandle=prehandle)
