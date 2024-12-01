import typing as t

from pydantic import AliasPath, BaseModel, Field


class PowCfg(BaseModel):
    prefix: str
    md5: str


class CommonCaptchaConf(BaseModel):
    pow_cfg: PowCfg
    """Ians, duration = match_md5(pow_cfg)"""
    tdc_path: str
    """relative path to get tdc.js"""


class CommonClickConf(BaseModel):
    data_type: str = Field(validation_alias=AliasPath("data_type", 0))
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


class CaptchaData(BaseModel):
    common: CommonCaptchaConf = Field(alias="comm_captcha_cfg")
    render: dict[str, t.Any] = Field(alias="dyn_show_info")


class PrehandleResp(BaseModel):
    captcha: t.Optional[CaptchaData] = Field(alias="data", default=None)
    sess: str

    capclass: int = 0
    log_js: str = ""
    randstr: str = ""
    sid: str = ""
    src_1: str = ""
    src_2: str = ""
    src_3: str = ""
    state: int = 0
    subcapclass: int = 0
    ticket: str = ""
    uip: str = ""
    """ipv4 / ipv6"""
