from .._model import PrehandleResp
from ..capsess import BaseTcaptchaSession


class ClickCaptchaSession(BaseTcaptchaSession):
    def __init__(self, session: str, prehandle: PrehandleResp) -> None:
        super().__init__(session, prehandle)
        self.mouse_track.set_result(None)
