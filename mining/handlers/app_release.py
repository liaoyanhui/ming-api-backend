import os
import io
from typing import Any, Dict
from webargs.aiohttpparser import use_kwargs, use_args
from marshmallow import fields
from aiohttp import web
from mining import apk_channel_builder
from mining.utils import load_android_apk_file, store_android_apk_to_temp_file
import logging

logger = logging.getLogger('app_release')


@use_kwargs({'release_id': fields.Int(data_key='releaseId'), 'file_name': fields.Str(data_key='fileName')}, location='match_info')
@use_kwargs({'referral_code': fields.Str(data_key='referralCode', missing=None)}, location='query')
async def download_android_release_apk_file(request: web.Request, release_id: int, file_name: str, referral_code: str) -> web.Response:
    android_apk = await request.app['db'].get_android_release_apk(release_id, file_name)
    if android_apk:
        await store_android_apk_to_temp_file(android_apk, release_id, file_name)
        f = io.BytesIO(android_apk)
    if f:
        f.seek(0, os.SEEK_SET)
        apk_channel_builder.build_channel(f, referral_code)
        content = f.read()
        return web.Response(content_type='application/vnd.android.package-archive',
                            headers={
                                'Content-Disposition': 'attachment; filename={}'.format(file_name)},
                            body=content)
    else:
        return web.Response(body='')

    # f = await load_android_apk_file(release_id, file_name)
    # if not f:
    #     android_apk = await request.app['db'].get_android_release_apk(release_id, file_name)
    #     if android_apk:
    #         await store_android_apk_to_temp_file(android_apk, release_id, file_name)
    #         f = io.BytesIO(android_apk)
    #         f.seek(0, os.SEEK_SET)

    # if f:
    #     f.seek(0, os.SEEK_SET)
    #     apk_channel_builder.build_channel(f, referral_code)
    #     content = f.read()
    #     return web.Response(content_type='application/vnd.android.package-archive',
    #         headers={'Content-Disposition': 'attachment; filename={}'.format(file_name)},
    #         body=content)
    # else:
    #     return web.Response(body='')


@use_kwargs({'referral_code': fields.Str(data_key='referralCode'), 'device_udid': fields.Str(data_key='deviceUDID')}, location='query')
async def enroll_preinstall_app_device(request: web.Request, referral_code: str, device_udid: str) -> web.Response:
    await request.app['db'].enroll_preinstall_app_device(referral_code, device_udid)
    return web.json_response({})
