import re
import typing as t
from contextlib import suppress

from aiohttp import ClientResponse
from lxml.html import HtmlElement, document_fromstring
from pydantic import AliasChoices, AliasPath, BaseModel, Field, HttpUrl, model_validator
from tenacity import TryAgain
from typing_extensions import Self

from aioqzone.exception import QzoneError
from aioqzone.utils.regex import entire_closing, response_callback
from qqqr.utils.iter import firstn
from qqqr.utils.jsjson import JsonValue, json_loads

from .feed import FeedData
from .profile import ProfileFeedData, QzoneProfile

StrDict = t.Dict[str, JsonValue]

__all__ = [
    "QzoneResponse",
    "FeedPageResp",
    "ProfileResp",
    "IndexPageResp",
    "ProfilePagePesp",
    "DetailResp",
    "FeedCount",
    "SingleReturnResp",
    "AddCommentResp",
    "PublishMoodResp",
    "DeleteUgcResp",
    "UploadPicResponse",
    "PhotosPreuploadResponse",
    "FeedData",
    "PicInfo",
    "ProfileFeedData",
]


class QzoneResponse(BaseModel):
    _errno_key: t.ClassVar[t.Union[str, AliasPath, AliasChoices, None]] = AliasChoices(
        "code", "ret", "err", "error"
    )
    _msg_key: t.ClassVar[t.Union[str, AliasPath, AliasChoices, None]] = AliasChoices(
        "message", "msg"
    )
    _data_key: t.ClassVar[t.Union[str, AliasPath, AliasChoices, None]] = AliasPath("data")

    @classmethod
    def from_response_object(cls, obj: "StrDict") -> Self:
        """Parses the response text or object recieved from Qzone API.

        :param obj: the parsed response object. see `.response_to_object`
        :raise `aioqzone.exception.QzoneError`: if returned result code != 0

        :return: Self
        """

        class response_header(BaseModel):
            status: int = Field(default=0, validation_alias=cls._errno_key)
            message: str = Field(default="", validation_alias=cls._msg_key)

        header = response_header.model_validate(obj)
        if header.status != 0:
            if header.message:
                raise QzoneError(header.status, header.message, robj=obj)
            else:
                raise QzoneError(header.status, robj=obj)

        if cls._data_key is None:
            return cls.model_validate(obj)

        class data_wrapper(BaseModel):
            data: cls = Field(validation_alias=cls._data_key)

        return data_wrapper.model_validate(obj).data

    @classmethod
    async def response_to_object(cls, response: ClientResponse) -> "StrDict":
        return await response.json(content_type=None)


class FeedCount(QzoneResponse):
    active_cnt: int = 0
    passive_cnt: int = 0
    gamebar_cnt: int = 0
    gift_cnt: int = 0
    visitor_cnt: int = 0


class DetailResp(FeedData, QzoneResponse):
    hasmore: bool = False
    attach_info: str = ""

    @model_validator(mode="before")
    def remove_prefix(cls, v: dict):
        return {k[5:] if str.startswith(k, "cell_") else k: i for k, i in v.items()}


class FeedPageResp(QzoneResponse):
    """Represents RESPonse from get feed page operation.
    Used to validate response data in :meth:`aioqzone.api.h5.QzoneH5API.index`
    and :meth:`aioqzone.api.h5.QzoneH5API.getActivateFeeds`
    """

    hasmore: bool = False
    attachinfo: str = ""
    newcnt: int

    undeal_info: FeedCount
    vFeeds: t.List[FeedData]


class ProfileResp(FeedPageResp):
    vFeeds: t.List[ProfileFeedData]


class IndexPageResp(FeedPageResp):
    qzonetoken: str = ""

    @classmethod
    async def response_to_object(cls, response: ClientResponse):
        html = await response.text()
        scripts: t.List[HtmlElement] = document_fromstring(html).xpath(
            'body/script[@type="application/javascript"]'
        )
        if not scripts:
            raise TryAgain("script tag not found")

        texts: t.List[str] = [s.text for s in scripts]
        script = firstn(texts, lambda s: "shine0callback" in s)
        if not script:
            raise TryAgain("data script not found")

        m = re.search(r'window\.shine0callback.*return "([0-9a-f]+?)";', script)
        if m is None:
            raise TryAgain("data script not found")
        qzonetoken = m.group(1)

        m = re.search(r"var FrontPage =.*?data\s*:\s*\{", script)
        if m is None:
            raise TryAgain("page data not found")
        data = script[m.end() - 1 : m.end() + entire_closing(script[m.end() - 1 :])]
        data = json_loads(data)
        with suppress(TypeError):
            data["data"]["qzonetoken"] = qzonetoken  # type: ignore

        return data


class QzoneStatistic(BaseModel):
    blog: int = 0
    message: int = 0
    pic: int = 0
    shuoshuo: int = 0


class QzoneInfo(QzoneResponse):
    count: QzoneStatistic
    cover: HttpUrl = Field(validation_alias=AliasPath("coverinfo", 0, "cover"))
    is_friend: bool
    is_hide: int
    limit: int
    profile: QzoneProfile


class ProfilePagePesp(QzoneResponse):
    info: QzoneInfo
    feedpage: ProfileResp
    qzonetoken: str

    @classmethod
    async def response_to_object(cls, response: ClientResponse):
        html = await response.text()
        scripts: t.List[HtmlElement] = document_fromstring(html).xpath(
            'body/script[@type="application/javascript"]'
        )
        if not scripts:
            raise TryAgain("script tag not found")

        texts: t.List[str] = [s.text for s in scripts]
        script = firstn(texts, lambda s: "shine0callback" in s)
        if not script:
            raise TryAgain("data script not found")

        m = re.search(r'window\.shine0callback.*return "([0-9a-f]+?)";', script)
        if m is None:
            raise TryAgain("data script not found")
        qzonetoken = m.group(1)

        m = re.search(r"var FrontPage =.*?data\s*:\s*\[", script)
        if m is None:
            raise TryAgain("page data not found")
        data = script[m.end() - 1 : m.end() + entire_closing(script[m.end() - 1 :], "[")]
        data = re.sub(r",,\]$", "]", data)
        data = json_loads(data)
        assert isinstance(data, list)
        if len(data) < 2:
            raise TryAgain("profile not returned")

        data = dict(zip(["info", "feedpage"], data))
        data["qzonetoken"] = qzonetoken
        return data

    @classmethod
    def from_response_object(cls, obj: "StrDict") -> Self:
        return cls(
            info=QzoneInfo.from_response_object(obj["info"]),  # type: ignore
            feedpage=ProfileResp.from_response_object(obj["feedpage"]),  # type: ignore
            qzonetoken=obj["qzonetoken"],  # type: ignore
        )


class SingleReturnResp(QzoneResponse):
    _data_key = None
    pass


class AddCommentResp(QzoneResponse):
    ret: int = 0
    msg: str = ""
    verifyurl: str = ""
    commentid: int = 0
    commentLikekey: HttpUrl


class PublishMoodResp(QzoneResponse):
    ret: int = 0
    msg: str = ""
    fid: str = Field(validation_alias="tid")
    undeal_info: FeedCount = Field(default_factory=FeedCount)


class DeleteUgcResp(QzoneResponse):
    ret: int = 0
    msg: str = ""
    undeal_info: FeedCount = Field(default_factory=FeedCount)


class UploadPicResponse(QzoneResponse):
    _data_key = None

    filelen: int
    filemd5: str

    @classmethod
    async def response_to_object(cls, response: ClientResponse):
        m = response_callback.search(await response.text())
        assert m
        return json_loads(m.group(1))


class PicInfo(QzoneResponse):
    _data_key = None

    pre: HttpUrl
    url: HttpUrl
    sloc: str
    lloc: str
    width: int
    height: int
    albumid: str


class PhotosPreuploadResponse(QzoneResponse):
    _data_key = None
    photos: t.List[PicInfo] = Field(default_factory=list)

    @classmethod
    async def response_to_object(cls, response: ClientResponse):
        m = response_callback.search(await response.text())
        assert m

        picinfos = json_loads(m.group(1))
        assert isinstance(picinfos, list)
        return dict(photos=[PicInfo.from_response_object(info["picinfo"]) for info in picinfos])  # type: ignore
