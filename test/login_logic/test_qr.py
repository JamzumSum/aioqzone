from __future__ import annotations

import asyncio
import io
from os import environ
from typing import TYPE_CHECKING, Optional

import pytest
import pytest_asyncio
from PIL import Image as image

from qqqr.constant import StatusCode
from qqqr.exception import UserBreak
from qqqr.qr import QrLogin, QrSession

pytestmark = pytest.mark.asyncio(scope="module")
skip_ci = pytest.mark.skipif(bool(environ.get("CI")), reason="Skip QR loop in CI")

if TYPE_CHECKING:
    from test.conftest import test_env

    from qqqr.utils.net import ClientAdapter

NoneType = type(None)


@pytest_asyncio.fixture(scope="class")
async def login(client: ClientAdapter, env: test_env):
    login = QrLogin(client, env.uin)
    login.qr_fetched.add_impl(
        lambda png, times, qr_renew=False: image.open(io.BytesIO(png)).show() if png else None
    )

    yield login


@pytest_asyncio.fixture(scope="class")
async def qrsess(login: QrLogin):
    yield await login.new()


class TestSession:
    async def test_new(self, qrsess: QrSession):
        assert isinstance(qrsess.current_qr.sig, str)

    async def test_poll(self, login: QrLogin, qrsess: QrSession):
        poll = await login.poll(qrsess)
        assert poll
        assert poll.code == StatusCode.Waiting


class TestLoop:
    @skip_ci
    async def test_loop(self, login: QrLogin):
        cookie = await login.login()
        assert cookie["p_skey"]
        assert cookie["pt_guid_sig"]

    async def test_resend_cancel(self, login: QrLogin):
        hist = []
        login.qr_cancelled.add_impl(lambda: hist.append("cancel"))

        async def __qr_fetched(png: Optional[bytes], times: int, qr_renew=False):
            hist.append(png)
            if len(hist) == 1:
                assert times == 0
                assert not qr_renew
                login.refresh.set()
            elif len(hist) == 2:
                assert times == 0
                assert qr_renew
                login.cancel.set()

        login.qr_fetched.impls.clear()
        login.qr_fetched.add_impl(__qr_fetched)
        with pytest.raises(UserBreak):
            await asyncio.wait_for(login.login(), timeout=3)

        assert len(hist) == 3
        assert hist[-1] == "cancel"
        assert isinstance(hist[0], (bytes, NoneType))
        assert isinstance(hist[1], (bytes, NoneType))
        assert type(hist[0]) == type(hist[1])
        assert hist[0] != hist[1]
