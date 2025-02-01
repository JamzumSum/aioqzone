from __future__ import annotations

from os import environ
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio

from qqqr.constant import StatusCode
from qqqr.exception import TencentLoginError
from qqqr.up import UpH5Login, UpWebLogin

if TYPE_CHECKING:
    from test.conftest import test_env

    from qqqr.utils.net import ClientAdapter

pytestmark = pytest.mark.asyncio(scope="module")
skip_ci = pytest.mark.skipif(bool(environ.get("CI")), reason="Skip QR loop in CI")


@pytest_asyncio.fixture(scope="module")
async def web(client: ClientAdapter, env: test_env):
    yield UpWebLogin(
        client,
        env.uin,
        env.password.get_secret_value(),
    )


class TestUpWeb:
    @skip_ci
    async def testRegisterSmsCodeGetter(self, web: UpWebLogin):
        async def GetSmsCode(uin: int, phone: str, nickname: str):
            assert phone
            assert nickname
            with open("tmp/ntdin.txt") as f:
                return f.readline().strip()

        web.sms_code_input.add_impl(GetSmsCode)

    async def test_encode_password(self, web: UpWebLogin):
        sess = await web.new()
        await web.check(sess)
        if sess.code == StatusCode.NeedCaptcha:
            try:
                await sess.pass_vc(web.captcha)
            except NotImplementedError:
                if web.captcha.solve_select_captcha.has_impl:
                    pytest.fail("cannot solve captcha")
                pytest.xfail("cannot solve captcha")
        if sess.code != 1:
            assert sess.verifycode
            assert sess.check_rst.salt
            p = await web.pwder.encode(sess.check_rst.salt, sess.verifycode)
            assert len(p) > 4
            r = await web.try_login(sess)
            assert r.code != StatusCode.WrongPassword

    async def test_login(self, web: UpWebLogin):
        try:
            cookies = await web.login()
        except TencentLoginError as e:
            if e.code in [StatusCode.RiskyNetwork, StatusCode.ForceQR]:
                pytest.skip(str(e))
            elif e.code == StatusCode.NeedSmsVerify:
                if not web.sms_code_input.has_impl:
                    pytest.skip(str(e))
            elif e.code == StatusCode.NeedCaptcha:
                if not web.captcha.solve_select_captcha.has_impl:
                    pytest.skip("cannot solve captcha")
            raise

        assert cookies["p_skey"]
        assert cookies["pt_guid_sig"]


@pytest.fixture
def h5(client: ClientAdapter, env: test_env):
    yield UpH5Login(
        client,
        env.uin,
        env.password.get_secret_value(),
    )


async def test_h5_login(h5: UpH5Login):
    try:
        cookies = await h5.login()
    except TencentLoginError as e:
        if e.code in [StatusCode.RiskyNetwork, StatusCode.ForceQR]:
            pytest.skip(str(e))
        elif e.code == StatusCode.NeedSmsVerify:
            if not h5.sms_code_input.has_impl:
                pytest.skip(str(e))
        elif e.code == StatusCode.NeedCaptcha:
            if not h5.captcha.solve_select_captcha.has_impl:
                pytest.skip("cannot solve captcha")

        raise

    assert cookies["p_skey"]
    # assert cookies["pt_guid_sig"]
