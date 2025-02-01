import asyncio
import logging
import typing as t
from contextlib import suppress
from random import choices, randint

from pydantic import AliasPath, BaseModel, Field

from qqqr.message import solve_slide_captcha
from qqqr.utils.iter import first, firstn
from qqqr.utils.net import ClientAdapter

from .._model import CommonBgElmConf, CommonRender, Sprite
from ..capsess import BaseTcaptchaSession
from ..pil_utils import *

log = logging.getLogger(__name__)

try:
    from slide_tc import imitate_drag  # prefer to numpy version
except ImportError:

    def imitate_drag(x1: int, x2: int, y: int) -> t.Tuple[t.List[int], t.List[int]]:
        """
        The imitate_drag function simulates a drag event.

        The function takes one argument, x, which is the number of pixels that the user drags.
        The function returns a tuple of lists containing three integers: [x_coordinate, y_coordinate].
        Each coordinate and time value is randomly generated according to corresponding rules.

        :param x1: Specify the position that the drag starts.
        :param x2: Specify the position that the drag ends.
        :param y: Specify the y-coordinate.
        :return: Two lists consist of the x coordinate and y coordinate
        """
        assert 0 < x1 < x2, (x1, x2)
        assert 0 < y, y

        n = randint(50, 64)
        noise_y = choices([y - 1, y + 1, y], [0.1, 0.1, 0.8], k=n)

        if n >= 51:
            noise_x = [0]
            noise_x += choices(list(range(-3, 4)), k=max(n - 51, 0))
        else:
            noise_x = []

        noise_x += choices(list(range(-2, 3)), k=30)
        noise_x += choices(list(range(-1, 2)), k=19)
        noise_x.append(0)

        d, lsv = (x1 - x2) / (n - 1), x1
        for i in range(n):
            noise_x[i] += round(lsv)
            lsv += d
        noise_x.sort()

        return noise_x, noise_y


class MoveCfg(BaseModel):
    track_limit: str
    move_factor: t.List[int]
    data_type: str = Field(validation_alias=AliasPath("data_type", 0))


class FgElemCfg(Sprite):
    id: int
    init_pos: t.List[int]
    move_cfg: t.Optional[MoveCfg] = None


class FgBindingCfg(BaseModel):
    master: int
    slave: int
    bind_type: str
    bind_factor: int


class SlideBgElemCfg(CommonBgElmConf, Sprite):
    img_url: str
    """relative url to get jigsaw puzzle image (background with dimmed piece shape)."""
    init_pos: t.List[int] = Field(default=[0, 0])
    """sprite init position on captcha (x, y)"""


class SlideRender(CommonRender):
    bg: SlideBgElemCfg = Field(alias="bg_elem_cfg")
    """Background (puzzle)"""
    fg_binding_list: t.List[FgBindingCfg] = Field(default=[])
    sprites: t.List[FgElemCfg] = Field(alias="fg_elem_list")
    """Foreground sprites"""
    sprite_url: str
    """relative url to get jigsaw piece (and handle) image."""


class SlideCaptchaSession(BaseTcaptchaSession):
    solve_captcha_hook: solve_slide_captcha.TyInst

    def parse_captcha_data(self):
        super().parse_captcha_data()
        self.render = SlideRender.model_validate(self.conf["render"])

        self.cdn_urls = (
            self._cdn_join(self.render.bg.img_url),
            self._cdn_join(self.render.sprite_url),
        )
        self.cdn_imgs: t.List[bytes] = []

        self.piece_sprite = first(self.render.sprites, lambda s: s.move_cfg)
        assert self.piece_sprite.move_cfg
        self.data_type = self.piece_sprite.move_cfg.data_type

    async def get_captcha_problem(self, client: ClientAdapter):
        """
        The get_captcha_problem function is a coroutine that accepts a TcaptchaSession object as an argument.
        It then uses the selfion to make an HTTP GET request to the captcha images (the problem). The images
        will be stored in the given selfion.

        :param self: captcha selfion
        :return: None
        """

        async def r(url) -> bytes:
            async with client.get(url) as r:
                r.raise_for_status()
                return await r.content.read()

        self.cdn_imgs = list(await asyncio.gather(*(r(i) for i in self.cdn_urls)))

    async def solve_captcha(self):
        """
        The solve_captcha function solves the captcha problem. It assumes that :obj:`TcaptchaSession.cdn_imgs`
        is already initialized, so call :meth:`.get_captcha_problem` firstly.

        It then solve the captcha as that in :class:`.Jigsaw`. The answer is saved into `self`.

        This function will also call :meth:`TDC.set_data` to imitate human behavior when solving captcha.

        :param self: Store the information of the current selfion
        :return: None
        """
        assert self.cdn_imgs

        if not self.solve_captcha_hook.has_impl:
            log.warning("solve_captcha_hook has no impls.")
            return ""

        background, piece = self.cdn_imgs
        piece_img = frombytes(piece).crop(self.piece_sprite.box)
        piece = tobytes(piece_img)

        left, top = self.piece_sprite.init_pos

        ans = None
        with suppress(asyncio.TimeoutError):
            hook_results = await self.solve_captcha_hook.results(background, piece, (left, top))
            # BUG: +1 to ensure left > init_pos[0], otherwise it's >=.
            # However if left == init_pos[0] + 1, it is certainly a wrong result.
            ans = firstn(hook_results, lambda i: i > left)

        if ans is None:
            return ""

        xs, ys = imitate_drag(left, ans, top)
        self.mouse_track.set_result(list(zip(xs, ys)))

        return f"{ans},{top}"
