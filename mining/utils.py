import asyncio
import re
from typing import Optional
import trafaret as T
import tempfile
import os
from pathlib import Path
import aiofiles
from mining import apk_channel_builder
import io

TRAFARET = T.Dict({
    T.Key('postgres'):
        T.Dict({
            'database': T.String(),
            'user': T.String(),
            'password': T.String(),
            'host': T.String(),
            'port': T.Int(),
            'minsize': T.Int(),
            'maxsize': T.Int(),
        }),
    T.Key('host'): T.IP,
    T.Key('port'): T.Int(),
})

async def invoke(func):
    result = func()
    if asyncio.iscoroutine(result):
        result = await result
    return result


def check_request(request, entries):
    for pattern in entries:
        if re.match(pattern, request.path):
            return True

    return False


def get_apk_local_store_location(apk_release_id: int):
    p = os.path.join(tempfile.gettempdir(), 'yunjie', 'android', 'release', str(apk_release_id))
    Path(p).mkdir(parents=True, exist_ok=True)
    return p


async def store_android_apk_to_temp_file(apk_buf: memoryview, apk_release_id: int, save_as_file_name: str):
    p = get_apk_local_store_location(apk_release_id)
    async with aiofiles.open(os.path.join(p, save_as_file_name), 'wb+') as f:
        await f.write(apk_buf)


async def load_android_apk_file(apk_release_id: int, load_file_name: str) -> Optional[io.BytesIO]:
    p = get_apk_local_store_location(apk_release_id)
    if Path(os.path.join(p, load_file_name)).exists():
        async with aiofiles.open(os.path.join(p, load_file_name), 'r+b') as f:
            content = await f.read()
            f = io.BytesIO(content)
            f.seek(0, os.SEEK_SET)
            return f
    


# @use_kwargs({'file_name': fields.Str(data_key='fileName')}, location='match_info')
# @use_kwargs({'referral_code': fields.Str(data_key='referralCode')}, location='query')
# async def download_android_release_apk_file(request: web.Request, file_name: str, referral_code: str) -> web.Response:
#     apk: memoryview = await request.app['db'].get_android_release_apk(file_name)
#     async with aiofiles.open(os.path.join(tempfile.gettempdir(), file_name), 'wb+') as f:
#         await f.write(apk)

#     async with aiofiles.open(os.path.join(tempfile.gettempdir(), file_name), 'r+b') as f:
#         await apk_channel_builder.build_channel(f, referral_code)

#         content = await f.read()
#         return web.Response(content_type='application/octet-stream',
#             headers={'Content-Disposition': 'attachment; filename={}'.format(file_name)},
#             body=content)


    