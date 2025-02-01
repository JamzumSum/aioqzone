import asyncio
import logging
import typing as t
from contextlib import suppress

from pydantic import AliasPath, BaseModel, Field, model_validator

from qqqr.message import solve_select_captcha
from qqqr.utils.iter import first
from qqqr.utils.jsjson import json_loads
from qqqr.utils.net import ClientAdapter

from .._model import CommonBgElmConf, CommonRender, PrehandleResp, Sprite
from ..capsess import BaseTcaptchaSession
from ..pil_utils import *

log = logging.getLogger(__name__)


class SelectBgElemCfg(CommonBgElmConf, Sprite):
    img_url: str


class SelectRegion(BaseModel):
    id: int
    box: t.Tuple[int, int, int, int] = Field(validation_alias="range")
    left: int = Field(validation_alias=AliasPath("range", 0))
    top: int = Field(validation_alias=AliasPath("range", 1))
    right: int = Field(validation_alias=AliasPath("range", 2))
    bottom: int = Field(validation_alias=AliasPath("range", 3))


class SelectJsonPayload(BaseModel):
    select_region_list: t.List[SelectRegion]
    prompt_id: int
    picture_ids: t.List[int]

    def __len__(self):
        return len(self.picture_ids)


class SelectRender(CommonRender):
    instruction: str
    bg: SelectBgElemCfg = Field(alias="bg_elem_cfg")
    verify_trigger_cfg: dict
    color_scheme: str  # pydantic_extra_types.color
    json_payload: SelectJsonPayload

    @model_validator(mode="before")
    def parse_json(cls, v: dict):
        v["json_payload"] = json_loads(v["json_payload"])
        return v


class SelectCaptchaSession(BaseTcaptchaSession):
    solve_captcha_hook: solve_select_captcha.TyInst

    def __init__(self, session: str, prehandle: "PrehandleResp") -> None:
        super().__init__(session, prehandle)
        self.mouse_track.set_result(None)

    def parse_captcha_data(self):
        super().parse_captcha_data()
        self.render = SelectRender.model_validate(self.conf["render"])
        self.data_type = self.render.bg.cfg["data_type"]

    async def get_captcha_problem(self, client: ClientAdapter):
        async with client.get(self._cdn_join(self.render.bg.img_url)) as r:
            img = frombytes(await r.content.read())

        imgs = {
            r.id: tobytes(img.crop(r.box)) for r in self.render.json_payload.select_region_list
        }
        self.cdn_imgs = [imgs[i] for i in self.render.json_payload.picture_ids]

    async def solve_captcha(self) -> str:
        if not self.solve_captcha_hook.has_impl:
            log.warning("solve_captcha_hook has no impls.")
            return ""

        ans = ()
        with suppress(asyncio.TimeoutError):
            hook_results = await self.solve_captcha_hook.results(
                self.render.instruction, tuple(self.cdn_imgs)
            )
            ans = first(hook_results, lambda i: bool(i), default=())
        return ",".join(str(self.render.json_payload.picture_ids[i - 1]) for i in ans)
