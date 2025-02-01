from os import environ

import pytest
import pytest_asyncio
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from qqqr.utils.net import ClientAdapter


class test_env(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="test_")
    uin: int = 0
    password: SecretStr = Field(default=SecretStr(""))


@pytest.fixture(scope="session")
def env():
    return test_env()


@pytest.fixture(scope="session")
def CI():
    return environ.get("CI") is not None


@pytest_asyncio.fixture(scope="module")
async def client():
    async with ClientAdapter() as client:
        yield client
