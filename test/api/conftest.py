from __future__ import annotations

import io
from os import environ
from typing import TYPE_CHECKING

import pytest_asyncio
from PIL import Image as image

from aioqzone.api import UpLoginConfig, UpLoginManager
from qqqr.utils.net import ClientAdapter

if TYPE_CHECKING:
    from test.conftest import test_env

loginman_list = ["up"]
if environ.get("CI") is None:
    loginman_list.append("qr")


@pytest_asyncio.fixture(scope="module", params=loginman_list)
async def man(request, client: ClientAdapter, env: test_env):
    if request.param == "up":
        return UpLoginManager(
            client,
            config=UpLoginConfig.model_validate(
                dict(uin=env.uin, pwd=env.password, fake_ip="8.8.8.8")
            ),
        )

    if request.param == "qr":
        from aioqzone.api import QrLoginConfig, QrLoginManager

        man = QrLoginManager(client, config=QrLoginConfig(uin=env.uin))
        man.qr_fetched.add_impl(
            lambda png, times, qr_renew=False: image.open(io.BytesIO(png)).show() if png else None
        )

        return man
