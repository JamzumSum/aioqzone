"""Response validation in `qqqr.up.captcha`"""

import typing as t

from pydantic import BaseModel, Field, HttpUrl, TypeAdapter

from qqqr.type import RedirectCookies


class CheckResp(t.NamedTuple):
    code: int
    """code = 0/2/3 hideVC; code = 1 showVC
    """
    verifycode: str
    salt_repr: t.Annotated[str, Field(alias="salt")]
    verifysession: str
    isRandSalt: int
    ptdrvs: str
    session: str

    @property
    def salt(self):
        salt = self.salt_repr.split(r"\x")[1:]
        salt = [chr(int(i, 16)) for i in salt]
        return "".join(salt)


class LoginResp(BaseModel):
    code: int
    url: t.Union[HttpUrl, str]
    msg: str
    nickname: str
    pt_ev_token: str = ""
    cookies: t.Optional[RedirectCookies] = None


class VerifyResp(BaseModel):
    code: int = Field(alias="errorCode")
    verifycode: str = Field(alias="randstr")
    ticket: str
    errMessage: str
    sess: str


CheckRespValidator = TypeAdapter(CheckResp)
