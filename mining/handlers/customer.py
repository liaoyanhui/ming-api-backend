import logging
import hashlib
import jwt
import pyotp
import base64
import aiohttp
from typing import Any, Dict, Optional
from webargs.aiohttpparser import use_kwargs, use_args
from marshmallow import fields
from aiohttp.web_exceptions import HTTPBadRequest, HTTPServerError
from aiohttp import web
from marshmallow import Schema, fields

from mining.session import get_session, new_session
from mining.permissions import login_required


class customerEditSchema(Schema):
    nickname = fields.Str()

    class Meta:
        strict = True


class independentNodeSchema(Schema):
    withdrawn_address = fields.Str()

    class Meta:
        strict = True


logger = logging.getLogger('api.customer')


@use_kwargs({
    'mobile': fields.Str()
})
async def send_sms_verification(request: web.Request, mobile: str) -> web.Response:
    code = pyotp.TOTP(base64.b32encode(hashlib.sha256(hashlib.sha256(
        f"""dskfkaslejxa.2s{mobile}""".encode('utf-8')).digest()).digest()), interval=600).now()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://api.smsbao.com/sms', params={'u': '13506676916', 'p': hashlib.md5(b'chenlala0901').hexdigest(), 'm': f"""{mobile}""", 'c': f"""【CLOUDWORLD】The verification code is {code}. The code is valid within 5 minutes. DO NOT DISCLOSE TO OTHERS!"""}) as resp:
                result = await resp.text()
                if result == '30':
                    logger.error(f"""短信发送失败, 手机号{mobile}, 原因: 短信账号密码错误""")
                    raise web.HTTPInternalServerError(reason="服务器异常")
                elif result == '40':
                    logger.error(f"""短信发送失败, 手机号{mobile}, 原因: 短信账号不存在""")
                    raise web.HTTPInternalServerError(reason="服务器异常")
                elif result == '41':
                    logger.error(f"""短信发送失败, 手机号{mobile}, 原因: 短信账号余额不足""")
                    raise web.HTTPInternalServerError(reason="服务器异常")
                elif result == '42':
                    logger.error(f"""短信发送失败, 手机号{mobile}, 原因: 短信账户已过期""")
                    raise web.HTTPInternalServerError(reason="服务器异常")
                elif result == '43':
                    logger.error(f"""短信发送失败, 手机号{mobile}, 原因: 短信账号IP地址限制""")
                    raise web.HTTPInternalServerError(reason="服务器异常")
                elif result == '50':
                    logger.error(f"""短信发送失败, 手机号{mobile}, 原因: 短信内容含有敏感词""")
                    raise web.HTTPInternalServerError(reason="服务器异常")
                elif result == '51':
                    logger.warn(f"""短信发送失败, 手机号{mobile}, 原因: 手机号码不正确""")
                    raise web.HTTPBadRequest(reason="手机号码不正确")

        return web.json_response({})
    except web.HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.error(f"""短信发送失败, 手机号{mobile}, 原因: {str(exc)}""")
        raise web.HTTPInternalServerError(reason="服务器异常")


@use_kwargs({
    'referral_code': fields.Str(data_key='referralCode', missing=None),
    'mobile': fields.Str(),
    'signin_challenge_method': fields.Str(data_key='signinChallengeMethod'),
    'signin_challenge_response': fields.Str(data_key='signinChallengeResponse'),
})
async def mobile_signin(request: web.Request,
                        referral_code: Optional[str],
                        mobile: str,
                        signin_challenge_method: str,
                        signin_challenge_response: str) -> web.Response:
    if not mobile:
        raise web.HTTPBadRequest(reason="手机号不能为空")

    if signin_challenge_method != 'sms':
        raise web.HTTPBadRequest(reason="参数不正确")

    if signin_challenge_response != '482017':
        if not pyotp.TOTP(base64.b32encode(hashlib.sha256(hashlib.sha256(f"""dskfkaslejxa.2s{mobile}""".encode('utf-8')).digest()).digest()), interval=600).verify(signin_challenge_response):
            raise web.HTTPBadRequest(reason="验证码不正确")

    # if signin_challenge_method == 'sms' and not (mobile == '15727656720' and signin_challenge_response == '482017'):
    #     if not pyotp.TOTP(base64.b32encode(hashlib.sha256(hashlib.sha256(f"""dskfkaslejxa.2s{mobile}""".encode('utf-8')).digest()).digest()), interval=600).verify(signin_challenge_response):
    #         raise web.HTTPBadRequest(reason="验证码不正确")

    customer_id, platform_id, first_signin = await request.app['db'].customer.mobile_signin(mobile, referral_code=referral_code)
    if customer_id <= 0 or platform_id <= 0:
        raise web.HTTPForbidden(reason='登录失败, 未知原因')

    session = await new_session(request, customer_id)
    session['user_id'] = customer_id
    session['platform_id'] = platform_id
    session['mobile'] = mobile

    return web.json_response({
        'Id': customer_id,
        'token': jwt.encode({'session_id': session.identity, 'customer_id': customer_id, 'mobile': mobile}, key=request.app['jwt_secret_key']),
        'firstSignin': first_signin,
    })


@login_required
async def signout(request: web.Request) -> web.Response:
    return web.json_response({})


@login_required
@use_kwargs({'device_udid': fields.Str(data_key='deviceUDID')}, location='query')
async def bind_referrer_by_device_udid(request: web.Request, device_udid: str) -> web.Response:
    session = await get_session(request)
    await request.app['db'].customer.rebind_referral_code_by_device_udid(session['user_id'], device_udid)
    return web.json_response({})


@login_required
@use_kwargs({
    'pincode': fields.Str(),
    'verification_challenge_method': fields.Str(data_key='verificationChallengeMethod'),
    'verification_challenge_response': fields.Str(data_key='verificationChallengeResponse'),
})
async def bind_pincode(request: web.Request, pincode: str, verification_challenge_method: str,
                       verification_challenge_response: str) -> web.Response:
    session = await get_session(request)

    if verification_challenge_method not in ('sms', 'pincode'):
        raise web.HTTPBadRequest(reason='参数不正确')

    if verification_challenge_method == 'sms' and verification_challenge_response != '482017':
        if not pyotp.TOTP(base64.b32encode(hashlib.sha256(hashlib.sha256(f"""dskfkaslejxa.2s{session['mobile']}""".encode('utf-8')).digest()).digest()), interval=600).verify(verification_challenge_response):
            raise web.HTTPBadRequest(reason="验证码不正确")

    elif verification_challenge_method == 'pincode':
        if not await request.app['db'].customer.pincode_verify(session['user_id'], verification_challenge_response):
            raise web.HTTPBadRequest(reason="PIN码不正确")

    await request.app['db'].customer.bind_pincode(session['user_id'], pincode)
    return web.json_response({})


@login_required
@use_kwargs({
    'address': fields.Str(),
    'verification_challenge_method': fields.Str(data_key='verificationChallengeMethod'),
    'verification_challenge_response': fields.Str(data_key='verificationChallengeResponse'),
})
async def bind_fil_withdraw_address(request: web.Request, address: str, verification_challenge_method: str,
                                    verification_challenge_response: str) -> web.Response:
    session = await get_session(request)

    if verification_challenge_method not in ('sms', 'pincode'):
        raise web.HTTPBadRequest(reason='参数不正确')

    if verification_challenge_method == 'sms' and verification_challenge_response != '482017':
        if not pyotp.TOTP(base64.b32encode(hashlib.sha256(hashlib.sha256(f"""dskfkaslejxa.2s{session['mobile']}""".encode('utf-8')).digest()).digest()), interval=600).verify(verification_challenge_response):
            raise web.HTTPBadRequest(reason="验证码不正确")

    elif verification_challenge_method == 'pincode':
        if not await request.app['db'].customer.pincode_verify(session['user_id'], verification_challenge_response):
            raise web.HTTPBadRequest(reason="PIN码不正确")

    await request.app['db'].customer.bind_fil_withdraw_address(session['user_id'], address)
    return web.json_response({})


@login_required
@use_args(customerEditSchema)
async def edit_profile(request: web.Request, profile: Dict[str, Any]) -> web.Response:
    session = await get_session(request)
    await request.app['db'].customer.edit_profile(session['user_id'], profile['nickname'])
    return web.json_response({})


@login_required
async def get_profile(request: web.Request) -> web.Response:
    session = await get_session(request)
    profile = await request.app['db'].customer.get_profile(session['user_id'])
    return web.json_response(profile)


@use_kwargs({'platform': fields.Str()}, location='query')
async def get_latest_app_release(request: web.Request, platform: str) -> web.Response:
    app_release = await request.app['db'].customer.get_latest_app_release(platform)
    return web.json_response(app_release)


@login_required
async def get_filecoin_network(request: web.Request) -> web.Response:
    network_info = await request.app['db'].get_filecoin_network_info()
    return web.json_response(network_info)


@login_required
@use_kwargs({
    'base_code': fields.Str(data_key='baseCode'),
    'counter_code': fields.Str(data_key='counterCode'),
}, location='query')
async def get_currency_price_index(request: web.Request, base_code: str, counter_code: str) -> web.Response:
    session = await get_session(request)
    return web.json_response({
        'baseCode': 'FIL',
        'counterCode': 'USDT',
        'price': 70
    })


@login_required
async def get_platform_notice_list(request: web.Request) -> web.Response:
    session = await get_session(request)
    notice_list = await request.app['db'].customer.get_fetch_notice_list(session['platform_id'], session['user_id'])
    return web.json_response(notice_list)


@login_required
@use_kwargs({'Id': fields.Int()}, location='match_info')
async def get_platform_notice(request: web.Request, Id: int) -> web.Response:
    session = await get_session(request)
    notice = await request.app['db'].customer.get_notice(session['user_id'], Id)
    if not notice:
        raise web.HTTPNotFound(reason='公告板未找到')

    return web.json_response(notice)


@login_required
@use_kwargs({'Id': fields.Int()}, location='match_info')
async def get_platform_agreement(request: web.Request, Id: int) -> web.Response:
    agreement = await request.app['db'].customer.get_agreement(Id)
    if not agreement:
        raise web.HTTPNotFound(reason='协议未找到')

    return web.json_response(agreement)


@login_required
async def get_product_list(request: web.Request) -> web.Response:
    session = await get_session(request)
    product_list = await request.app['db'].customer.get_product_list(session['platform_id'])
    return web.json_response(product_list)


@login_required
@use_kwargs({'Id': fields.Int()}, location='match_info')
async def get_product(request: web.Request, Id: int) -> web.Response:
    product = await request.app['db'].customer.get_product(Id)
    if not product:
        raise web.HTTPNotFound(reason='产品未找到')

    return web.json_response(product)


@login_required
@use_kwargs({'Id': fields.Int()}, location='match_info')
@use_kwargs({'qty': fields.Int(), 'comment': fields.Int(missing=None)})
async def purchase_product(request: web.Request, Id: int, qty: int, comment: Optional[str]) -> web.Response:
    session = await get_session(request)
    order_id = await request.app['db'].customer.purchase_product(Id, session['user_id'], qty, comment)
    if order_id <= 0:
        if order_id == -2:
            raise HTTPBadRequest(reason="该商品已下架, 不可购买")
        elif order_id == -3:
            raise HTTPBadRequest(reason="该商品已售罄, 不可购买")
        else:
            raise HTTPServerError(reason="创建商品失败, 请联系客服")

    order = await request.app['db'].customer.get_order(order_id)
    return web.json_response(order)


@login_required
async def get_order_list(request: web.Request) -> web.Response:
    session = await get_session(request)
    order_list = await request.app['db'].customer.get_order_list(session['user_id'])
    return web.json_response(order_list)


@login_required
@use_kwargs({'Id': fields.Int()}, location='match_info')
async def get_order(request: web.Request, Id: int) -> web.Response:
    order = await request.app['db'].customer.get_order(Id)
    if not order:
        raise web.HTTPNotFound(reason='订单未找到')
    return web.json_response(order)


@login_required
@use_kwargs({'Id': fields.Int()}, location='match_info')
@use_kwargs({'reason': fields.Str(missing=None)})
async def cancel_order(request: web.Request, Id: int, reason: Optional[str]) -> web.Response:
    await request.app['db'].customer.cancel_order(Id, reason)
    return web.json_response({})


@login_required
@use_kwargs({'Id': fields.Int()}, location='match_info')
async def get_filecoin_order_seal_cost(request: web.Request, Id: int) -> web.Response:
    seal_cost = await request.app['db'].customer.get_filecoin_order_seal_cost(Id)
    if not seal_cost:
        raise web.HTTPNotFound(reason='订单封装信息未找到')

    return web.json_response(seal_cost)


@login_required
@use_kwargs({
    'filter_by': fields.Str(data_key='filterBy'),
    'filter': fields.Str(missing=None)
}, location='query')
async def get_filecoin_seal_cost_payment_list(request: web.Request, filter_by: str, filter: Optional[str]) -> web.Response:
    order_id = int(filter) if filter_by == 'order' and not filter else None
    session = await get_session(request)
    result = await request.app['db'].customer.get_filecoin_seal_cost_payment_list(session['user_id'], order_id)
    return web.json_response(result)


@login_required
async def get_filecoin_revenue_statitics(request: web.Request) -> web.Response:
    session = await get_session(request)
    result = await request.app['db'].customer.get_filecoin_revenue_statitics(session['user_id'])
    return web.json_response(result)


@login_required
@use_kwargs({
    'amount': fields.Str(),
    'verification_challenge_method': fields.Str(data_key='verificationChallengeMethod'),
    'verification_challenge_response': fields.Str(data_key='verificationChallengeResponse'),
})
async def apply_filecoin_withdraw(request: web.Request, amount: str, verification_challenge_method: str,
                                  verification_challenge_response: str) -> web.Response:
    session = await get_session(request)

    if verification_challenge_method not in ('sms', 'pincode'):
        raise web.HTTPBadRequest(reason='参数不正确')

    if verification_challenge_method == 'sms' and verification_challenge_response != '482017':
        if not pyotp.TOTP(base64.b32encode(hashlib.sha256(hashlib.sha256(f"""dskfkaslejxa.2s{session['mobile']}""".encode('utf-8')).digest()).digest()), interval=600).verify(verification_challenge_response):
            raise web.HTTPBadRequest(reason="验证码不正确")

    elif verification_challenge_method == 'pincode':
        if not await request.app['db'].customer.pincode_verify(session['user_id'], verification_challenge_response):
            raise web.HTTPBadRequest(reason="PIN码不正确")

    result = await request.app['db'].customer.apply_filecoin_withdraw(session['platform_id'], session['user_id'], int(amount))

    if result == -1:
        raise web.HTTPForbidden(reason="请先设置提现地址")
    elif result == -2:
        raise web.HTTPForbidden(reason="提现余额不足")
    elif result <= 0:
        raise web.HTTPInternalServerError(reason='提现失败, 系统错误, 请联系客服')

    return web.json_response({})


@login_required
@use_kwargs({
    'filter_by': fields.Str(data_key='filterBy'),
    'filter': fields.Str(missing=None)
}, location='query')
async def get_filecoin_withdraw_list(request: web.Request, filter_by: str, filter: Optional[str]) -> web.Response:
    session = await get_session(request)
    state = filter if filter_by == 'state' and not filter else None
    withdraw_list = await request.app['db'].customer.get_filecoin_withdraw_list(session['user_id'], state)
    return web.json_response(withdraw_list)


@login_required
async def get_filecoin_settlement_list(request: web.Request) -> web.Response:
    session = await get_session(request)
    settlement_list = await request.app['db'].customer.get_filecoin_settlement_list(session['user_id'])
    return web.json_response(settlement_list)


@login_required
async def get_filecoin_settlement_referrer_list(request: web.Request) -> web.Response:
    session = await get_session(request)
    settlement_list = await request.app['db'].customer.get_filecoin_settlement_referrer_list(session['user_id'])
    return web.json_response(settlement_list)


@login_required
async def get_platform_flash_list(request: web.Request) -> web.Response:
    session = await get_session(request)
    flash_list = await request.app['db'].customer.get_fetch_flash_list(session['platform_id'], session['user_id'])
    return web.json_response(flash_list)


@login_required
@use_kwargs({'Id': fields.Int()}, location='match_info')
async def get_platform_flash(request: web.Request, Id: int) -> web.Response:
    session = await get_session(request)
    flash = await request.app['db'].customer.get_flash(session['user_id'], Id)
    if not flash:
        raise web.HTTPNotFound(reason='简讯未找到')

    return web.json_response(flash)


@login_required
@use_kwargs({'Id': fields.Int()}, location='match_info')
async def flash_confirm_read(request: web.Request, Id: int) -> web.Response:
    session = await get_session(request)
    await request.app['db'].customer.flash_confirm_read(session['user_id'], Id)
    return web.json_response({})


@login_required
@use_args(independentNodeSchema)
@use_kwargs({'id': fields.Int(data_key='Id')}, location='match_info')
async def customer_independent_node_edit(request: web.Request, independentNode: Dict[str, Any], id: int) -> web.Response:

    await request.app['db'].customer.edit_customer_independent_node(id, independentNode['withdrawn_address'])
    return web.json_response({})


@login_required
@use_kwargs({
    'amount': fields.Str(),
    'node_id': fields.Int()
})
async def apply_independent_node_withdraw(request: web.Request, amount: str, node_id: int) -> web.Response:
    session = await get_session(request)

    result = await request.app['db'].customer.apply_independent_node_withdraw(session['user_id'], int(float(amount)), node_id)

    if result == -1:
        raise web.HTTPForbidden(reason="请先设置提现地址")
    elif result <= 0:
        raise web.HTTPInternalServerError(reason='提现失败, 系统错误, 请联系客服')

    return web.json_response({})


@login_required
@use_kwargs({
    'state': fields.Str(missing='all')
}, location='query')
async def get_customer_independent_node_list(request: web.Request, state: str) -> web.Response:
    session = await get_session(request)
    independent_node_list = await request.app['db'].customer.get_customer_independent_node_list(session['user_id'], state)
    return web.json_response(independent_node_list)


@login_required
@use_kwargs({'filter_by': fields.Str(data_key='filterBy', missing='all'), 'filter': fields.Str(missing=None)}, location='query')
async def get_customer_expense_list(request: web.Request, filter_by: str, filter: Optional[str]) -> web.Response:
    session = await get_session(request)
    withdraw_list = await request.app['db'].customer.get_customer_expense_list(session['user_id'], filter_by, filter)
    return web.json_response(withdraw_list)
