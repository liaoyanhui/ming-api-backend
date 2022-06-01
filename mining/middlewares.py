'''
Description:
Author: 尚夏
Date: 2021-11-08 15:11:26
LastEditTime: 2021-12-07 17:14:40
FilePath: /mining-api-backend/mining/middlewares.py
'''
import traceback
import logging
import re
import jwt
from aiohttp import web, hdrs
from aiohttp.web_middlewares import _Handler, _Middleware
from mining.session import setup as session_setup, PgStorage

logger = logging.getLogger('mining')


def JWTMiddleware(secret_or_pub_key: str) -> _Middleware:

    @web.middleware
    async def factory(request: web.Request, handler: _Handler):
        if request.method == hdrs.METH_OPTIONS:
            return await handler(request)

        token = None
        if 'Authorization' in request.headers:
            try:
                schema, token = request.headers.get(
                    'Authorization').strip().split(' ')
            except ValueError:
                raise web.HTTPForbidden(reason='Invalid authorization header')

            if not re.match('Bearer', schema):
                raise web.HTTPForbidden(reason='Invalid token scheme')

        if token is not None:
            try:
                decoded = jwt.decode(
                    token, secret_or_pub_key, algorithms=["HS256"])
                request['token'] = decoded
            except jwt.InvalidTokenError as exc:
                raise web.HTTPUnauthorized(
                    f"""Invalid authorization token, {str(exc)}""")

        return await handler(request)
    return factory


@web.middleware
async def error_middleware(request: web.Request, handler: _Handler):
    try:
        return await handler(request)
    except web.HTTPException as exc:
        return web.json_response({'code': exc.status_code, 'message': exc.reason})
    except Exception as exc:
        logger.error(
            f"""handle request -> `{request.url} - {request.headers} - {request.query}` failed!!! reason: {str(exc)}""")
        logger.debug(traceback.print_exc())
        return web.json_response({'code': 500, 'message': str(exc)})


def get_session_id(request: web.Request) -> str:
    return request['token']['session_id'] if 'token' in request else None


def setup_middlewares(app: web.Application):
    app.middlewares.append(error_middleware)
    app.middlewares.append(JWTMiddleware(app['jwt_secret_key']))

    session_setup(app, PgStorage(app, get_session_id))
