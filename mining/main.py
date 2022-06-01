import logging
import sys

from aiohttp import web
from mining.db import setup as setup_db
from mining.jobs import setup as setup_jobs
from mining.middlewares import setup_middlewares
from mining.routes import setup_customer_routes, setup_platform_routes, setup_app_release_routes
from mining.settings import get_config
from mining.utils import store_android_apk_to_temp_file


async def on_startup(app: web.Application):
    android_release_id, android_file_name, android_apk = await app['db'].get_lastest_android_app_release()
    if android_release_id:
        await store_android_apk_to_temp_file(android_apk, android_release_id, android_file_name)


def main(argv):
    logging.basicConfig(level=logging.DEBUG)
    root = web.Application(client_max_size=1024**2*100)
    root['config'] = get_config(argv)
    setup_db(root)
    setup_jobs(root)

    app = setup_customer_routes(root)
    app['jwt_secret_key'] = 'adsfasfewfaj#kjf32'
    setup_middlewares(app)
    root.add_subapp('/fil/client/v1', app)

    app = setup_platform_routes(root)
    app['jwt_secret_key'] = 'adsfasfewfaj#kjf32'
    setup_middlewares(app)
    root.add_subapp('/fil/admin/v1', app)

    app = setup_app_release_routes(root)
    root.add_subapp('/app', app)

    root.on_startup.append(on_startup)

    web.run_app(root, host=root['config']['host'], port=root['config']['port'])


if __name__ == '__main__':
    main(sys.argv[1:])
