import typing as t
from enum import IntEnum

from pydantic import (
    AliasChoices,
    AliasPath,
    BaseModel,
    Field,
    HttpUrl,
    RootModel,
    field_validator,
    model_validator,
)

__all__ = ["FeedData"]


class UgcRight(IntEnum):
    unknown = 0
    all = 1
    qq = 4
    part = 16
    self = 64
    blacklist = 128


class RightInfo(BaseModel):
    ugc_right: int = UgcRight.unknown
    allow_uins: t.List = Field(default_factory=list)


class FeedCommon(BaseModel):
    time: int
    appid: int
    typeid: int = Field(alias="feedstype")
    curkey: t.Union[HttpUrl, str] = Field(alias="curlikekey", union_mode="left_to_right")
    orgkey: t.Union[HttpUrl, str] = Field(alias="orglikekey", union_mode="left_to_right")
    ugckey: str
    """an underscore-joined string including `uin`, `appid`, `ugcrightkey`"""
    ugcrightkey: str
    """an identifier, for most 311 feeds, it equals to cellid (fid)."""
    right_info: RightInfo
    wup_feeds_type: int

    subid: int = 0
    originaltype: int = 0


class UserInfo(BaseModel):
    uin: int = Field(validation_alias=AliasChoices("uin", AliasPath("user", "uin")))
    nickname: str = Field(
        default="", validation_alias=AliasChoices("nickname", AliasPath("user", "nickname"))
    )


class FeedSummary(BaseModel):
    summary: str = ""
    hasmore: bool = False

    @property
    def has_more(self):
        return self.hasmore or len(self.summary) >= 499


class LikeInfo(BaseModel):
    isliked: bool = False
    likeNum: int = Field(validation_alias="num", default_factory=int)
    likemans: t.List[UserInfo] = Field(default_factory=list)


class PhotoUrl(BaseModel):
    height: int
    width: int
    url: HttpUrl

    md5: str = ""
    size: int = 0

    def __hash__(self) -> int:
        o = (self.__class__.__name__, self.height, self.width, self.url)
        return hash(o)

    def __eq__(self, o) -> bool:
        return (
            isinstance(o, PhotoUrl)
            and (o.url == self.url)
            and (o.width == self.width)
            and (o.height == self.height)
        )

    @property
    def area(self):
        return self.height * self.width


class PhotoUrls(RootModel[t.Set[PhotoUrl]]):
    @model_validator(mode="before")
    def unpack_urls(cls, v: dict):
        return list(v.values())

    @property
    def largest(self) -> PhotoUrl:
        return max(self.root, key=lambda p: p.area)

    @property
    def smallest(self) -> PhotoUrl:
        return min(self.root, key=lambda p: p.area)

    @property
    def urls(self):
        return self.root


class FeedVideo(BaseModel):
    videoid: str
    videourl: t.Union[HttpUrl, t.Literal[""], None]
    # videourls: dict
    coverurl: PhotoUrls
    videotime: int

    videotype: int = 0
    albumid: str = ""
    video_max_playtime: int = 0


class PicData(BaseModel):
    photourl: PhotoUrls
    videodata: FeedVideo
    videoflag: int = 0

    albumid: str
    curkey: str = Field(validation_alias="curlikekey")

    origin_size: int
    origin_height: int
    origin_width: int
    origin_phototype: int = 0

    # @model_validator(mode="before")
    # def remove_useless_data(cls, v: dict):
    #     if "videodata" in v:
    #         if not v["videodata"]["videourl"]:
    #             del v["videodata"]
    #     return v


class FeedPic(BaseModel):
    albumid: str
    uin: int
    picdata: t.List[PicData]


class CommentItem(LikeInfo):
    commentid: int
    commentLikekey: HttpUrl
    content: str
    date: int
    user: UserInfo
    isDeleted: bool = False
    isPrivate: bool = False

    likeNum: int = Field(default_factory=int)
    replynum: int
    commentpic: t.List = Field(default_factory=list)
    replys: t.List = Field(default_factory=list)
    # picdata: dict


class FeedComment(BaseModel):
    num: int = 0
    unreadCnt: int = 0
    comments: t.List[CommentItem] = Field(default_factory=list)


class HasCommon(BaseModel):
    common: FeedCommon = Field(validation_alias="comm")

    @property
    def abstime(self):
        return self.common.time


class HasUserInfo(BaseModel):
    userinfo: UserInfo


class HasSummary(BaseModel):
    summary: FeedSummary = Field(default_factory=FeedSummary)


class HasMedia(BaseModel):
    pic: t.Optional[FeedPic] = None
    video: t.Optional[FeedVideo] = None


class HasFid(BaseModel):
    fid: str = Field(validation_alias=AliasPath("id", "cellid"))


class ShareInfo(BaseModel):
    summary: str = ""
    title: str = ""
    photourl: t.Optional[PhotoUrls] = None

    # @model_validator(mode="before")
    # def remove_empty_photourl(cls, v: dict):
    #     if not v.get("photourl"):
    #         v["photourl"] = None
    #     return v


class Share(HasCommon):
    common: FeedCommon = Field(validation_alias="cell_comm")


class FeedOriginal(HasFid, HasCommon, HasUserInfo, HasSummary, HasMedia):
    @model_validator(mode="before")
    def remove_prefix(cls, v: dict[str, t.Any]):
        return {k.removeprefix("cell_"): i for k, i in v.items()}

    @field_validator("summary")
    @classmethod
    def remove_colon(cls, v: FeedSummary):
        v.summary = v.summary.removeprefix("：")
        return v


class FeedData(HasFid, HasCommon, HasSummary, HasMedia, HasUserInfo):
    like: LikeInfo = Field(default_factory=LikeInfo)

    comment: FeedComment = Field(default_factory=FeedComment)
    original: t.Union[FeedOriginal, Share, None] = Field(default=None, union_mode="left_to_right")
    share_info: ShareInfo = Field(
        default_factory=ShareInfo, validation_alias=AliasPath("operation", "share_info")
    )
