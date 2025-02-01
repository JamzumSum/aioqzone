import typing as t

from pydantic import AliasPath, BaseModel, Field, TypeAdapter
from typing_extensions import TypedDict


class PowCfg(TypedDict):
    prefix: str
    md5: str


class CommonCaptchaConf(TypedDict):
    pow_cfg: PowCfg
    """Ians, duration = match_md5(pow_cfg)"""
    tdc_path: str
    """relative path to get tdc.js"""


class CommonClickConf(TypedDict):
    data_type: t.Annotated[str, Field(validation_alias=AliasPath("data_type", 0))]
    mark_style: str


class CommonBgElmConf(BaseModel):
    cfg: CommonClickConf = Field(validation_alias="click_cfg")


class CommonRender(BaseModel):
    bg: CommonBgElmConf = Field(validation_alias="bg_elem_cfg")


class Sprite(BaseModel):
    """Represents a sprite from a source material."""

    size_2d: t.List[int]
    """sprite size (w, h)"""
    sprite_pos: t.List[int]
    """sprite position on material (x, y)"""

    @property
    def height(self):
        return self.size_2d[1]

    @property
    def width(self):
        return self.size_2d[0]

    @property
    def box(self):
        l, t = self.sprite_pos
        return (l, t, l + self.width, l + self.height)


class CaptchaData(TypedDict):
    common: t.Annotated[CommonCaptchaConf, Field(alias="comm_captcha_cfg")]
    render: t.Annotated[dict[str, t.Any], Field(alias="dyn_show_info")]


class PrehandleResp(TypedDict):
    captcha: t.Annotated[t.Optional[CaptchaData], Field(alias="data", default=None)]
    sess: str

    capclass: t.Annotated[int, Field(default=0)]
    log_js: t.Annotated[str, Field(default="")]
    randstr: t.Annotated[str, Field(default="")]
    sid: t.Annotated[str, Field(default="")]
    src_1: t.Annotated[str, Field(default="")]
    src_2: t.Annotated[str, Field(default="")]
    src_3: t.Annotated[str, Field(default="")]
    state: t.Annotated[int, Field(default=0)]
    subcapclass: t.Annotated[int, Field(default=0)]
    ticket: t.Annotated[str, Field(default="")]
    uip: t.Annotated[str, Field(default="")]
    """ipv4 / ipv6"""


PrehandleRespValidator = TypeAdapter(PrehandleResp)
