from __future__ import annotations

import asyncio
import io
from os import environ
from typing import TYPE_CHECKING, Type, cast
from unittest.mock import patch

import pytest
import pytest_asyncio
from aiohttp import ClientConnectionError as ConnectError
from aiohttp import ClientResponseError
from aiohttp import RequestInfo as Request
from PIL import Image as image
from tenacity import TryAgain

from aioqzone.api import QrLoginConfig, QrLoginManager, UpLoginConfig, UpLoginManager
from aioqzone.exception import UnexpectedLoginError
from qqqr.exception import TencentLoginError, UserBreak
from qqqr.utils.net import ClientAdapter

if TYPE_CHECKING:
    from test.conftest import test_env

    from qqqr.utils.net import ClientAdapter

pytestmark = pytest.mark.asyncio(scope="module")
skip_ci = pytest.mark.skipif(bool(environ.get("CI")), reason="Skip QR loop in CI")

_fake_request = cast(Request, ...)
_fake_http_error = ClientResponseError(_fake_request, (), status=403)


@pytest_asyncio.fixture
async def up(client: ClientAdapter, env: test_env):
    yield UpLoginManager(client, config=UpLoginConfig(uin=env.uin, pwd=env.password))


class TestUP:
    @pytest.mark.parametrize(
        ["exc2r", "exc2e"],
        [
            (TencentLoginError(-3002, "mock"), TencentLoginError),
            (TencentLoginError(-3000, "请重新登录"), TryAgain),
            (NotImplementedError(), TencentLoginError),
            (GeneratorExit(), TryAgain),
            (ConnectError("mock"), TryAgain),
            (_fake_http_error, TryAgain),
            (SystemExit(), UnexpectedLoginError),
        ],
    )
    async def test_exception(
        self, up: UpLoginManager, exc2r: BaseException, exc2e: Type[BaseException]
    ):
        with patch.object(up.uplogin, "login", side_effect=exc2r), pytest.raises(exc2e):
            await up._new_cookie()

    async def test_newcookie(self, up: UpLoginManager):
        pool = []
        up.login_success.add_impl(lambda uin: pool.append(uin))
        up.login_failed.add_impl(lambda uin, exc: pool.append(exc))

        success = await up.new_cookie()
        assert up.last_login > 0
        await up.ch_login_notify.wait()
        assert pool

        if not success:
            pytest.skip(str(pool[0]))

        assert "p_skey" in up.cookie
        assert up.uin == pool[0]
        assert up.cookie
        assert up.gtk > 0


@pytest_asyncio.fixture
async def qr(client: ClientAdapter, env: test_env):
    man = QrLoginManager(client, config=QrLoginConfig(uin=env.uin))

    man.qr_fetched.add_impl(
        lambda png, times, qr_renew=False: image.open(io.BytesIO(png)).show() if png else None
    )
    yield man


class TestQR:
    @pytest.mark.parametrize(
        ["exc2r", "exc2e"],
        [
            (UserBreak, UserBreak),
            (asyncio.CancelledError, UserBreak),
            (GeneratorExit(), TryAgain),
            (ConnectError("mock"), TryAgain),
            (_fake_http_error, TryAgain),
            (SystemExit, UnexpectedLoginError),
        ],
    )
    async def test_exception(
        self, qr: QrLoginManager, exc2r: BaseException, exc2e: Type[BaseException]
    ):
        with patch.object(qr.qrlogin, "login", side_effect=exc2r), pytest.raises(exc2e):
            await qr._new_cookie()

    @skip_ci
    async def test_newcookie(self, qr: QrLoginManager):
        pool = []
        qr.login_success.add_impl(lambda uin: pool.append(uin))
        qr.login_failed.add_impl(lambda uin, exc: pool.append(exc))

        success = await qr.new_cookie()
        assert qr.last_login > 0
        await qr.ch_login_notify.wait()
        assert pool

        if not success:
            pytest.skip(str(pool[0]))

        assert "p_skey" in qr.cookie
        assert qr.uin == pool[0]
        assert qr.cookie
        assert qr.gtk > 0
