from http.cookies import SimpleCookie
from typing import Dict

from aiohttp import ClientResponse as Response
from aiohttp import ClientResponseError
from aiohttp import ClientSession as ClientAdapter

__all__ = ["raise_for_status", "get_all_cookie", "ClientAdapter"]


def raise_for_status(response: Response, *accept_code: int):
    """A checker more strict than :meth:`~aiohttp.ClientResponse.raise_for_status`.

    :param response: Client response to check.
    :param accept_code: Overwrite codes that can be accepted, If not given, default is `(200, )`

    :raise `aiohttp.ClientResponseError`: if status not in :obj:`accept_code`
    """
    response.raise_for_status
    accept_code = accept_code or (200,)
    if response.status not in accept_code:
        response.release()
        raise ClientResponseError(
            response.request_info,
            response.history,
            status=response.status,
            message=response.reason or f"{response.status} not in {accept_code}",
            headers=response.headers,
        )


def get_all_cookie(response: Response) -> Dict[str, str]:
    """An adapter to get all response cookies from a response object."""
    cookies = SimpleCookie()
    for i in response.headers.getall("Set-Cookie"):
        if not "=;" in i:
            cookies.load(i)
    return {k: v.value for k, v in cookies.items() if v.value}


def use_mobile_ua(client: ClientAdapter):
    from ..constant import AndroidUA

    client.headers["User-Agent"] = AndroidUA
