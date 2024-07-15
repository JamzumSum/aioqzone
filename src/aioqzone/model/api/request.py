import typing as t
from base64 import b64encode
from io import BytesIO
from math import floor
from os import PathLike
from time import time

from pydantic import BaseModel, Field, field_serializer, field_validator
from typing_extensions import Buffer

from aioqzone.utils.time import time_ms

from .feed import UgcRight
from .response import PicInfo, UploadPicResponse

__all__ = [
    "QzoneRequestParams",
    "ActiveFeedsParams",
    "GetFeedsParams",
    "ProfileParams",
    "ShuoshuoParams",
    "GetCountParams",
    "DolikeParam",
    "AddCommentParams",
    "PublishMoodParams",
    "DeleteUgcParams",
    "UploadPicParams",
    "PhotosPreuploadParams",
    "UgcRight",
    "PhotoData",
]


class QzoneRequestParams(BaseModel):
    uin_fields: t.ClassVar[t.Tuple[str, ...]] = ()
    ts_fields: t.ClassVar[t.Tuple[str, ...]] = ()

    def build_params(self, uin: int, timestamp: t.Optional[float] = None):
        d = self.model_dump(mode="json", by_alias=True)
        d.update({i: uin for i in self.uin_fields})
        if self.ts_fields:
            timestamp = time_ms(timestamp)
            d.update({i: timestamp for i in self.ts_fields})
        return d


class ActiveFeedsParams(QzoneRequestParams):
    attach_info: str


class GetFeedsParams(QzoneRequestParams):
    hostuin: int
    attach_info: str = Field(default="", serialization_alias="res_attach")

    res_type: int = 2
    refresh_type: int = 2
    format: str = "json"


class ProfileParams(QzoneRequestParams):
    hostuin: int
    start_time: float = Field(default=0, serialization_alias="starttime")
    ts_fields = ("starttime",)

    @field_serializer("start_time")
    def ms(self, start_time: float):
        return int(1e3 * start_time)


class ShuoshuoParams(QzoneRequestParams):
    fid: str = Field(serialization_alias="cellid")
    uin: int = Field(alias="uin")
    appid: int = Field(default=311)
    busi_param: str = Field(default="", max_length=100)

    format: str = "json"
    count: int = 20
    refresh_type: int = 31
    subid: str = ""


class GetCountParams(QzoneRequestParams):
    format: str = "json"


class DolikeParam(QzoneRequestParams):
    uin_fields = ("opuin",)
    unikey: str
    curkey: str
    appid: int
    opr_type: str = "like"
    format: str = "purejson"


class AddCommentParams(QzoneRequestParams):
    uin_fields = ("uin",)
    ownuin: int
    fid: str = Field(serialization_alias="srcId")
    private: int = Field(serialization_alias="isPrivateComment")
    content: str = Field(min_length=1, max_length=2000)
    appid: int = Field(default=311)

    bypass_param: dict = Field(default_factory=dict)
    busi_param: dict = Field(default_factory=dict)


class PhotoData(BaseModel):
    albumid: str
    lloc: str
    sloc: str
    type: str = ""
    height: int = 0
    width: int = 0
    origin_uuid: str = ""
    origin_height: int = 0
    origin_width: int = 0

    def to_richval(self):
        richval: t.List[str] = [
            self.albumid,
            self.lloc,
            self.sloc,
            self.type,
            str(self.height),
            str(self.width),
            self.origin_uuid,
            str(self.origin_height or ""),
            str(self.origin_width or ""),
        ]
        return ",".join(richval)

    @classmethod
    def from_PicInfo(cls, o: PicInfo):
        return cls.model_validate(o, from_attributes=True)


class PublishMoodParams(QzoneRequestParams):
    uin_fields = ("res_uin",)
    content: str = Field(min_length=1, max_length=2000)
    photos: t.List[PhotoData] = Field(default_factory=list, serialization_alias="richval")
    sync_weibo: int = Field(
        default=False, validate_default=True, serialization_alias="issyncweibo"
    )
    ugc_right: UgcRight = UgcRight.all

    opr_type: str = "publish_shuoshuo"
    format: str = "json"
    # lat: int
    # lon: int
    # lbsid: str = "poiinfo_district"

    @field_serializer("photos")
    def richval(self, photos: t.List[PhotoData]):
        return " ".join(i.to_richval() for i in photos)


class DeleteUgcParams(QzoneRequestParams):
    uin_fields = ("res_uin",)
    appid: int = Field(serialization_alias="res_type")
    fid: str = Field(serialization_alias="res_id")

    opr_type: str = "delugc"
    real_del: int = 0
    format: str = "json"


class UploadPicParams(QzoneRequestParams):
    uin_fields = ("uin",)
    picture: bytes
    hd_height: int
    hd_width: int
    hd_quality: int = 70

    # defaults
    base64: int = 1
    output_type: str = "json"
    preupload: int = 1
    charset: str = "utf-8"
    output_charset: str = "utf-8"
    logintype: str = "sid"
    Exif_CameraMaker: str = ""
    Exif_CameraModel: str = ""
    Exif_Time: str = ""

    @field_serializer("picture", return_type=str)
    def b64_picture(self, picture: t.ByteString) -> str:
        return b64encode(picture).decode()

    @classmethod
    def from_image(cls, image_file: t.Union[str, PathLike, t.IO[bytes]], quality=70):
        import PIL.Image as image

        with image.open(image_file) as f:
            buf = BytesIO()
            f.save(buf, "JPEG", quality=quality)
            return cls(
                picture=buf.getvalue(), hd_height=f.height, hd_width=f.width, hd_quality=quality
            )

    @classmethod
    def from_bytes(cls, image_bytes: Buffer, quality=70):
        buf = BytesIO(image_bytes)
        return cls.from_image(buf, quality=quality)


class PhotosPreuploadParams(QzoneRequestParams):
    uin_fields = ("uin",)
    upload_pics: t.List[UploadPicResponse] = Field(exclude=True)

    cur_num: int = Field(default=0, serialization_alias="currnum")
    upload_hd: int = 0

    # defaults
    preupload: int = 2
    output_type: str = "json"
    uploadtype: int = 1
    albumtype: int = 7
    big_style: int = 1
    op_src: int = 15003
    charset: str = "utf-8"
    output_charset: str = "utf-8"
    refer: str = "shuoshuo"

    @property
    def uploadNum(self):
        return len(self.upload_pics)

    def build_params(self, uin: int, timestamp: t.Optional[float] = None):
        assert self.upload_pics

        params = super().build_params(uin=uin, timestamp=timestamp)
        timestamp = timestamp or time()
        batchid = time_ms(timestamp) * 1000
        uploadtime = floor(timestamp)
        params.update(batchid=batchid, uploadtime=uploadtime)

        md5, size = [], []
        for pic in self.upload_pics:
            md5.append(pic.filemd5)
            size.append(str(pic.filelen))

        params.update(md5="|".join(md5), filelen="|".join(size))
        return params
