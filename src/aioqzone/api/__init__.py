"""
Make some easy-to-use api from basic wrappers.
"""
from ..type import AlbumData
from ..type import FeedDetailRep
from ..type import FeedMoreAux
from ..type import FeedRep
from ..type import FeedsCount
from ..type import FloatViewPhoto
from ..type import MsgListElm
from .raw import QzoneApi


class DummyQapi(QzoneApi):
    async def feeds3_html_more(
        self,
        pagenum: int,
        trans: QzoneApi.FeedsMoreTransaction = None,
        count: int = 10
    ) -> tuple[list[FeedRep], FeedMoreAux]:
        r = await super().feeds3_html_more(pagenum, trans=trans, count=count)
        data = r['data']
        main = r['main']
        assert isinstance(data, list)
        return [FeedRep.parse_obj(i) for i in data if i], FeedMoreAux.parse_obj(main)

    async def emotion_getcomments(self, uin: int, tid: str, feedstype: int) -> str:
        r = await super().emotion_getcomments(uin, tid, feedstype)
        return str.strip(r['newFeedXML'])    # type: ignore

    async def emotion_msgdetail(self, owner: int, fid: str) -> FeedDetailRep:
        r = await super().emotion_msgdetail(owner, fid)
        return FeedDetailRep.parse_obj(r)

    async def get_feeds_count(self) -> FeedsCount:
        r = await super().get_feeds_count()
        return FeedsCount.parse_obj(r)

    async def floatview_photo_list(self, album: AlbumData, num: int) -> list[FloatViewPhoto]:
        r = await super().floatview_photo_list(album, num)
        return [FloatViewPhoto.parse_obj(i) for i in r['photos']]    # type: ignore

    async def emotion_msglist(self, uin: int, num: int = 20, pos: int = 0) -> list[MsgListElm]:
        r = await super().emotion_msglist(uin, num, pos)
        return [MsgListElm.parse_obj(i) for i in r]
