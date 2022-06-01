'''
Description: 
Author: 尚夏
Date: 2021-12-08 15:00:15
LastEditTime: 2022-02-16 14:49:00
FilePath: /mining-api-backend/mining/permissions.py
'''
from typing import Any, Awaitable, Callable, Optional
from aiohttp import web

from .session import get_session, get_platform_session

_Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]


def login_required(fn: _Handler) -> _Handler:
    async def wrapped(request: web.Request, *args: Any, **kwargs: Any) -> web.StreamResponse:
        session = await get_session(request)
        if not session.user_id:
            raise web.HTTPUnauthorized(reason="请先登录")
        return await fn(request, *args, **kwargs)  # type: ignore[call-arg]

    return wrapped


def platform_login_required(fn: _Handler) -> _Handler:
    async def wrapped(request: web.Request, *args: Any, **kwargs: Any) -> web.StreamResponse:
        session = await get_platform_session(request)
        if not session.user_id:
            raise web.HTTPUnauthorized(reason="请先登录")

        return await fn(request, *args, **kwargs)  # type: ignore[call-arg]

    return wrapped
