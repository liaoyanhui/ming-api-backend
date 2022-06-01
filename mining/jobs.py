from datetime import datetime
import logging
from operator import ne
import aiohttp
import lxml.html
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json
import math

from trafaret import And

HEADERS = {
    'USER-AGENT': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.85 Safari/537.36',
}

logger = logging.getLogger('jobs')


def unit_transfer(original: str, method: str, count: int, splitCount: int):
    p = abs(float(original))
    if method == "MUL":
        p = p * math.pow(1024, count)
    elif method == "DIV":
        p = p / math.pow(1024, count)
    if float(original) < 0:
        return f"""-{format(p, f'.{splitCount}f')}"""
    else:
        return format(p, f'.{splitCount}f')


async def craw_network_info(app: web.Application):
    try:
        async with aiohttp.ClientSession() as session:
            data = {"id": 1, "jsonrpc": "2.0",
                    "method": 'filscan.StatChainInfo'}
            async with session.post('https://api.filscan.io:8700/rpc/v1', data=json.dumps(data).encode("utf-8"), headers=HEADERS) as response:
                async with session.get('https://api.coingecko.com/api/v3/simple/price?ids=binance-peg-filecoin&vs_currencies=usd', headers=HEADERS) as priceResopnse:
                    res = await response.json()
                    priceRes = await priceResopnse.json()
                    if res['result']:
                        data = res['result']['data']
                        network_info = {
                            'filPrice': f"""${priceRes['binance-peg-filecoin']['usd']}""",
                            'networkStoragePower': unit_transfer(data['total_quality_power'], 'DIV', 6, 4) + ' EiB',
                            'latest24hPowerGrowth': unit_transfer(data['power_increase_24h'], 'DIV', 5, 4) + ' PiB',
                            'latest24hEfficiencny': unit_transfer(data['fil_per_tera'], 'EQUAL', 1, 4) + ' FIL/TiB',
                            'sectorInitialPledge': unit_transfer(data['pledge_per_tera'], 'EQUAL', 1, 4) + ' FIL/TiB',
                            'gasUsedOf32GSector': unit_transfer(data['gas_in_32g'], 'EQUAL', 1, 4) + ' FIL/TiB',
                            'gasUsedOf64GSector': unit_transfer(data['gas_in_64g'], 'EQUAL', 1, 4) + ' FIL/TiB',
                            'costOfSeal32GSector': unit_transfer(data['add_power_in_32g'], 'EQUAL', 1, 4) + ' FIL/TiB',
                            'costOfSeal64GSector': unit_transfer(data['add_power_in_64g'], 'EQUAL', 1, 4) + ' FIL/TiB',
                        }
                        await app['db'].update_filecoin_network_info(network_info)
    except Exception as exc:
        logger.error(f"""Craw netowrk info failed, reason: {str(exc)}""")


async def start_jobs(app: web.Application):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(craw_network_info, 'interval', args=[
                      app, ], minutes=5, next_run_time=datetime.now())
    scheduler.start()
    app['scheduler'] = scheduler


async def stop_jobs(app: web.Application):
    app['scheduler'].shutdown()


def setup(app: web.Application):
    app.on_startup.append(start_jobs)
    app.on_cleanup.append(stop_jobs)
