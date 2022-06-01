from datetime import date
import logging
import hashlib
from typing import Any, Dict, Optional
from aiohttp.web_response import Response
import jwt
import pyotp
import base64
import json

from aiohttp.web_exceptions import HTTPBadRequest, HTTPForbidden, HTTPServerError
from webargs.aiohttpparser import use_kwargs, use_args
from marshmallow import Schema, fields

import aiohttp
from aiohttp import web

from mining.session import get_platform_session, new_platform_session
from mining.permissions import platform_login_required


logger = logging.getLogger('api.platform')


class FiatPayMethodSchema(Schema):
    icon = fields.Str()
    bank_name = fields.Str(data_key='bankName')
    account_name = fields.Str(data_key='accountName')
    account_no = fields.Str(data_key='accountNo')
    comment = fields.Str()

    class Meta:
        strict = True


class ContactDetailScheam(Schema):
    wechat_number = fields.Str(data_key='wechatNumber')
    wechat_business_card = fields.Str(data_key='wechatBusinessCard')
    mobile = fields.Str()

    class Meta:
        strict = True


class PlatformSettingSchema(Schema):
    is_self_operated = fields.Bool(data_key='isSelfOperated')
    is_demo_platform = fields.Bool(data_key='isDemoPlatform')
    language = fields.Str(data_key='language')
    filecoin_storage_product_service_fee_percent = fields.Int(
        data_key="filecoinStorageProductServiceFeePercent")
    referrer_commission_rate = fields.Int(data_key='referrerCommissionRate')
    product_purchase_specifiction = fields.Str(
        data_key='productPurchaseSpecifiction')

    class Meta:
        strict = True


class CreatePlatformSchema(Schema):
    name = fields.Str()
    is_self_operated = fields.Bool(data_key='isSelfOperated', missing=False)
    is_demo_platform = fields.Bool(data_key='isDemoPlatform', missing=False)
    intro = fields.Str(missing=None)
    language = fields.Str(missing='zh')
    settings = fields.Nested(PlatformSettingSchema, missing=None)

    class Meta:
        strict = True


class AppRelaseSchema(Schema):
    version = fields.Str()
    platform = fields.Str()
    release_notes = fields.Str(data_key='releaseNotes')
    download_url = fields.Str(data_key='downloadURL', missing=None)
    comment = fields.Str(missing=None)

    class Meta:
        strict = True


class PlatformEditSchema(Schema):
    name = fields.Str()
    carousels_album_id = fields.Int(data_key='carouselsAlbumId')
    referrer_album_id = fields.Int(data_key='referrerAlbumId')
    intro = fields.Str()
    language = fields.Str()
    order_pay_methods = fields.List(fields.Nested(
        FiatPayMethodSchema), data_key='orderPaymethods')
    user_service_agreement_id = fields.Int(data_key='userServiceAgreementId')
    privacy_policy_agreement_id = fields.Int(
        data_key='privacyPolicyAgreementId')
    sales_contract_and_hosting_service_agreement_id = fields.Int(
        data_key='salesContractAndHostingServiceAgreementId')
    about_us_agreement_id = fields.Int(data_key='aboutUsAgreementId')
    customer_service_contact = fields.Nested(
        ContactDetailScheam, data_key="customerServiceContact")

    class Meta:
        strict = True


class AgreementSchema(Schema):
    title = fields.Str()
    content = fields.Str()

    class Meta:
        strict = True


class NoticeSchema(Schema):
    title = fields.Str()
    content = fields.Str()
    display_popup = fields.Boolean(data_key='displayPopup', missing=False)
    read_confirm = fields.Boolean(data_key='readConfirm', missing=False)

    class Meta:
        strict = True


class flashSchema(Schema):
    title = fields.Str()
    content = fields.Str()
    display_popup = fields.Boolean(data_key='displayPopup', missing=False)
    read_confirm = fields.Boolean(data_key='readConfirm', missing=False)

    class Meta:
        strict = True


class PhotoSchema(Schema):
    album_id = fields.Int(data_key='albumId', missing=None)
    mime_type = fields.Str(data_key='mimeType')
    height = fields.Int()
    width = fields.Int()
    photo = fields.Str(data_key='data')

    class Meta:
        strict = True


class CustomerSchema(Schema):
    mobile = fields.Str(missing=None)
    nick_name = fields.Str(data_key='nickName', missing=None)
    remarks_name = fields.Str(data_key='internalRemarksName', missing=None)
    description = fields.Str(missing=None)
    referrer_customer_id = fields.Int(
        data_key='referrerCustomerId', missing=None)

    class Meta:
        strict = True


class ProductSchema(Schema):
    name = fields.Str(required=True)
    sale_unit = fields.Int(data_key='saleUnit', required=True)
    min_units_for_sale = fields.Int(data_key='minUnitsForSale', required=True)
    stock_qty = fields.Int(data_key='stockQty', required=True)
    price = fields.Int(required=True)
    market_price = fields.Int(data_key='marketPrice', required=True)
    service_fee_percent = fields.Int(
        data_key='serviceFeePercent', required=True)
    hosting_days = fields.Int(data_key='hostingDays', required=True)
    cover = fields.Int(required=True)
    photos = fields.Int(required=True)
    sale_method = fields.Str(data_key='saleMethod', missing='byStorage')
    sale_keywords = fields.List(
        fields.Str(), data_key='saleKeywords', missing=[])
    intro = fields.Str(required=True)
    description = fields.Str(required=True)

    class Meta:
        strict = True


class PurchaseProductSchema(Schema):
    customer_id = fields.Int(data_key='customerId', required=True)
    qty = fields.Int(required=True)
    paid_amount = fields.Int(data_key='paidAmount', required=True)
    grant_qty = fields.Int(data_key='grantQty', missing=0)
    internal_comment = fields.Str(data_key='internalComment', missing=None)

    class Meta:
        strict = True


class OrderFiatPaymentSchema(Schema):
    order_id = fields.Int(data_key='orderId', required=True)
    bank_name = fields.Str(data_key='bankName', required=True)
    bank_statement_no = fields.Str(data_key='bankStatementNo', required=True)
    amount = fields.Int(required=True)
    payment_screenshots = fields.Str(
        data_key='paymentScreenshots', missing=None)
    comment = fields.Str(missing=None)

    class Meta:
        strict = True


class OrderCryptoPaymentSchema(Schema):
    order_id = fields.Int(data_key='orderId', required=True)
    currency = fields.Str(required=True)
    amount = fields.Int(required=True)
    tx_or_message_id = fields.Str(data_key='txOrMessageId', required=True)
    comment = fields.Str(missing=None)

    class Meta:
        strict = True


class OrderFilecoinSealCostPayment(Schema):
    order_id = fields.Int(data_key='orderId', required=True)
    type = fields.Str(data_key='type', required=True)
    message_id = fields.Str(data_key='messageId', required=True)
    to_address = fields.Str(data_key='toAddress', required=True)
    amount = fields.Int(data_key='amount', required=True)
    comment = fields.Str(missing=None)

    class Meta:
        strict = True


class customerNodeSchema(Schema):
    customer_id = fields.Int(data_key='customerId', required=True)
    node_no = fields.Str(data_key='nodeNo', required=True)
    node_comment = fields.Str(data_key='nodeComment', missing=None)

    class Meta:
        strict = True


class independentNodeSchema(Schema):
    node_no = fields.Str(missing=None)
    node_comment = fields.Str(missing=None)
    withdrawn_address = fields.Str(missing=None)

    class Meta:
        strict = True


class customerExpensesSchema(Schema):
    customer_id = fields.Int(data_key='customerId', required=True)
    expenses_type = fields.Str(data_key='expensesType', required=True)
    expenses_amount = fields.Int(data_key='expensesAmount', required=True)
    reason = fields.Str(data_key='reason', required=True)
    comment = fields.Str(data_key='comment', missing=None)

    class Meta:
        strict = True


@use_kwargs({
    'mobile': fields.Str(),
    'signin_challenge_method': fields.Str(data_key='signinChallengeMethod'),
    'signin_challenge_response': fields.Str(data_key='signinChallengeResponse'),
})
async def mobile_signin(request: web.Request, mobile: str, signin_challenge_method: str, signin_challenge_response: str) -> web.Response:
    if not mobile:
        raise web.HTTPBadRequest(reason="手机号不能为空")

    if signin_challenge_method != 'sms':
        raise web.HTTPBadRequest(reason="参数不正确")

    if signin_challenge_response != '482017':
        if not pyotp.TOTP(base64.b32encode(hashlib.sha256(hashlib.sha256(f"""dskwdzkasel3232*&^zejxa.2s{mobile}""".encode('utf-8')).digest()).digest()), interval=600).verify(signin_challenge_response):
            raise web.HTTPBadRequest(reason="验证码不正确")

    status_code, result = await request.app['db'].platform.mobile_signin(mobile)
    if status_code == -1:
        raise HTTPBadRequest(reason='账号错误')
    if status_code == -2:
        raise HTTPBadRequest(reason='此账号已被管理员禁用')

    session = await new_platform_session(request, result['Id'])
    session['user_id'] = result['Id']
    session['platform_ids'] = result['platformIds']
    session['mobile'] = result['mobile']
    session['nick_name'] = result['nickName']
    session['user_role'] = result['userRole']
    session['is_platform_admin'] = True

    return web.json_response({
        'Id':           session['user_id'],
        'mobile':       session['mobile'],
        'userRole':     session['user_role'],
        'platformIds':  session['platform_ids'],
        'token':        jwt.encode({'session_id': session.identity, 'admin_id': result['Id'], 'mobile': result['mobile'], 'user_role': result['userRole']}, key=request.app['jwt_secret_key'])
    })


@use_kwargs({'mobile': fields.Str()})
async def send_sms_verification(request: web.Request, mobile: str) -> None:
    code = pyotp.TOTP(base64.b32encode(hashlib.sha256(hashlib.sha256(
        f"""dskwdzkasel3232*&^zejxa.2s{mobile}""".encode('utf-8')).digest()).digest()), interval=600).now()
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


@platform_login_required
async def signout(request: web.Request) -> web.Response:
    return web.json_response({})


@platform_login_required
@use_args(CreatePlatformSchema)
async def owner_create_platform(request: web.Request, platform: Dict[str, Any]) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    id = await request.app['db'].platform.owner_create_platform(
        platform['name'],
        platform['is_self_operated'],
        platform['is_demo_platform'],
        platform['intro'],
        platform['language'],
        json.dumps({
            'filecoin_storage_product_service_fee_percent': platform['settings']['filecoin_storage_product_service_fee_percent'],
            'referrer_commission_rate': platform['settings']['referrer_commission_rate'],
            'product_purchase_specifiction': platform['settings']['product_purchase_specifiction']
        }) if platform['settings'] else None)

    if id:
        session['platform_ids'] = session['platform_ids'] + [id, ]

    return web.json_response({'Id': id})


@platform_login_required
@use_args(AppRelaseSchema)
async def owner_create_app_release(request: web.Request, release: Dict[str, Any]) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.owner_create_app_release(
        release['version'],
        release['platform'],
        release['release_notes'],
        release['download_url'],
        release['comment'])

    return web.json_response({})


@platform_login_required
@use_args(AppRelaseSchema)
@use_kwargs({'Id': fields.Int()}, location='match_info')
async def owner_edit_app_release(request: web.Request, release: Dict[str, Any], Id: int) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.owner_edit_app_release(
        Id,
        release['version'],
        release['platform'],
        release['release_notes'],
        release['download_url'],
        release['comment'])
    return web.json_response({})


@platform_login_required
@use_kwargs({'Id': fields.Int()}, location='match_info')
async def owner_app_release_publish(request: web.Request, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.owner_app_release_publish(Id)
    return web.json_response({})


@platform_login_required
@use_kwargs({'Id': fields.Int()}, location='match_info')
async def owner_app_release_revoke(request: web.Request, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.owner_app_release_revoke(Id)
    return web.json_response({})


@platform_login_required
@use_kwargs({'Id': fields.Int()}, location='match_info')
async def owner_upload_android_release_apk(request: web.Request, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')
    post = await request.post()
    apk = post.get('androidAPK', None)
    if apk:
        await request.app['db'].platform.owner_upload_android_release_apk(Id, apk.filename, apk.file)

    return web.json_response({})


@platform_login_required
async def owner_fetch_app_release_list(request: web.Request) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    release_list = await request.app['db'].platform.owner_fetch_app_release_list()
    return web.json_response(release_list)


@platform_login_required
async def owner_get_platform_list(request: web.Request) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    platforms = await request.app['db'].platform.owner_fetch_platform_list()
    return web.json_response(platforms)


@platform_login_required
@use_args(PlatformSettingSchema)
@use_kwargs({'Id': fields.Int()}, location='match_info')
async def owner_setting_platform(request: web.Request, settings: Dict[str, Any], Id: int) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.owner_setting_platform(Id,
                                                            settings['is_self_operated'],
                                                            settings['is_demo_platform'],
                                                            settings['language'],
                                                            json.dumps({
                                                                'filecoin_storage_product_service_fee_percent': settings['filecoin_storage_product_service_fee_percent'],
                                                                'referrer_commission_rate': settings['referrer_commission_rate'],
                                                                'product_purchase_specifiction': settings['product_purchase_specifiction']}))

    return web.json_response({})


@platform_login_required
@use_kwargs({'Id': fields.Int()}, location='match_info')
@use_kwargs({'customer_id': fields.Int(data_key='customerId'), 'new_platform_id': fields.Int(data_key='newPlatformId')}, location='query')
async def owner_rebind_customer_to_platform(request: web.Request, Id: int, customer_id: int, new_platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    id = await request.app['db'].platform.owner_rebind_customer_to_platform(Id, customer_id, new_platform_id)

    return web.json_response({'Id': id})


@platform_login_required
@use_args(PlatformEditSchema)
@use_kwargs({'Id': fields.Int()}, location='match_info')
async def edit_platform(request: web.Request, platform: Dict[str, Any], Id: int) -> web.Response:
    session = await get_platform_session(request)
    if Id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')
    await request.app['db'].platform.edit_platform(Id,
                                                   platform['name'],
                                                   platform['carousels_album_id'],
                                                   platform['referrer_album_id'],
                                                   platform['intro'],
                                                   platform['language'],
                                                   platform['order_pay_methods'],
                                                   platform['user_service_agreement_id'],
                                                   platform['privacy_policy_agreement_id'],
                                                   platform['sales_contract_and_hosting_service_agreement_id'],
                                                   platform['about_us_agreement_id'],
                                                   platform['customer_service_contact'])
    return web.json_response({})


@platform_login_required
@use_kwargs({'Id': fields.Int()}, location='match_info')
async def get_platform(request: web.Request, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if Id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    platform = await request.app['db'].platform.get_platform(Id)
    return web.json_response(platform)


@platform_login_required
async def get_filecoin_network(request: web.Request) -> web.Response:
    network_info = await request.app['db'].get_filecoin_network_info()
    return web.json_response(network_info)


@platform_login_required
@use_kwargs({'day_at': fields.Date(data_key='dayAt')}, location='query')
async def get_filecoin_mining_efficiency(request: web.Request, day_at: date) -> web.Response:
    mining_efficiency = await request.app['db'].get_filecoin_mining_efficiency(day_at)
    return web.json_response({'miningEfficiency': int(mining_efficiency)})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def get_agreement_list(request: web.Request, platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    agreements = await request.app['db'].platform.fetch_agreement_list(platform_id)
    return web.json_response(agreements)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def get_agreement(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    agreements = await request.app['db'].platform.get_agreement(Id)
    return web.json_response(agreements)


@platform_login_required
@use_args(AgreementSchema)
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def create_agreement(request: web.Request, agreement: Dict[str, Any], platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    id = await request.app['db'].platform.create_agreement(platform_id, agreement['title'], agreement['content'])
    return web.json_response({'Id': id})


@platform_login_required
@use_args(AgreementSchema)
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def edit_agreement(request: web.Request, agreement: Dict[str, Any], platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    id = await request.app['db'].platform.edit_agreement(Id, agreement['title'], agreement['content'])
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def get_notice(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    notice = await request.app['db'].platform.get_notice(Id)
    return web.json_response(notice)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def get_notice_list(request: web.Request, platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    notice = await request.app['db'].platform.fetch_notice_list(platform_id)
    return web.json_response(notice)


@platform_login_required
@use_args(NoticeSchema)
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def create_notice(request: web.Request, notice: Dict[str, Any], platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    id = await request.app['db'].platform.create_notice(
        platform_id, notice['title'], notice['content'], notice['display_popup'], notice['read_confirm'])
    return web.json_response({'Id': id})


@platform_login_required
@use_args(NoticeSchema)
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def edit_notice(request: web.Request, notice: Dict[str, Any], platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.edit_notice(
        Id, notice['title'], notice['content'], notice['display_popup'], notice['read_confirm'])
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def publish_notice(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.publish_notice(Id)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def revoke_notice(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.revoke_notice(Id)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({'title': fields.Str()})
async def create_albums(request: web.Request, platform_id: int, title: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    id = await request.app['db'].platform.create_album(platform_id, title)
    return web.json_response({'Id': id})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def get_photo(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    photo = await request.app['db'].platform.get_photo(platform_id, Id)
    return web.json_response(photo)


@platform_login_required
@use_args(PhotoSchema)
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def upload_photo(request: web.Request, photo: Dict[str, Any], platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    id = await request.app['db'].platform.upload_photo(
        platform_id, photo['mime_type'], photo['height'], photo['width'], photo['photo'], photo['album_id'])
    return web.json_response({'Id': id})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def remove_photo(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.remove_photo(Id)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def get_customer(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    customer = await request.app['db'].platform.get_customer(Id)
    return web.json_response(customer)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
@use_kwargs({'referrer_id': fields.Int(data_key='referrerId')}, location='query')
async def rebind_customer_referrer(request: web.Request, platform_id: int, Id: int, referrer_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.rebind_customer_referrer(Id, referrer_id, platform_id)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({'filter_by': fields.Str(data_key='filterBy', missing='all'), 'filter': fields.Str(missing=None)}, location='query')
async def get_customer_list(request: web.Request, platform_id: int, filter_by: str, filter: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    customers = await request.app['db'].platform.fetch_customer_list(platform_id, filter_by, filter)
    return web.json_response(customers)


@platform_login_required
@use_args(CustomerSchema)
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def create_customer(request: web.Request, customer: Dict[str, Any], platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    if customer['mobile'] is None:
        raise HTTPBadRequest('参数错误')

    id = await request.app['db'].platform.create_customer(
        platform_id, customer['mobile'], customer['nick_name'], customer['remarks_name'], customer['description'], customer['referrer_customer_id'])
    return web.json_response({'Id': id})


@platform_login_required
@use_args(CustomerSchema)
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def edit_customer(request: web.Request, customer: Dict[str, Any], platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.edit_customer(Id, customer['nick_name'], customer['remarks_name'], customer['description'])
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def get_referrer_list(request: web.Request, platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    referrer_list = await request.app['db'].platform.fetch_referrer_list(platform_id)
    return web.json_response(referrer_list)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def get_referrer(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    referrer = await request.app['db'].platform.get_referrer(Id)
    return web.json_response(referrer)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def get_referrer_customer_list(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    customers = await request.app['db'].platform.get_referrer_customer_list(Id)
    return web.json_response(customers)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
@use_kwargs({'commission_rate': fields.Int(data_key='commissionRate')}, location='query')
async def set_referrer_commission(request: web.Request, platform_id: int, Id: int, commission_rate: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.set_referrer_commission(Id, commission_rate)
    return web.json_response({})


@platform_login_required
@use_args(ProductSchema)
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def create_product(request: web.Request, product: Dict[str, Any], platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    id = await request.app['db'].platform.create_product(platform_id,
                                                         product['name'], product['sale_method'], product[
                                                             'sale_unit'], product['min_units_for_sale'],
                                                         product['stock_qty'], product['price'], product[
                                                             'market_price'], product['service_fee_percent'],
                                                         product['hosting_days'], product['cover'], product['photos'], product['sale_keywords'],
                                                         product['intro'], product['description'])
    return web.json_response({'Id': id})


@platform_login_required
@use_args(ProductSchema)
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def edit_product(request: web.Request, product: Dict[str, Any], platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.edit_product(Id,
                                                  product['name'], product['sale_unit'], product['min_units_for_sale'], product['stock_qty'],
                                                  product['price'], product['market_price'], product[
                                                      'service_fee_percent'], product['hosting_days'],
                                                  product['cover'], product['photos'], product['sale_keywords'], product['intro'], product['description'])
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def get_product_list(request: web.Request, platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    platforms = await request.app['db'].platform.fetch_product_list(platform_id)
    return web.json_response(platforms)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def get_product(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    platform = await request.app['db'].platform.get_product(Id)
    return web.json_response(platform)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
@use_kwargs({'state': fields.Str()}, location='query')
async def change_product_state(request: web.Request, platform_id: int, Id: int, state: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.change_product_state(Id, state)
    return web.json_response({})


@platform_login_required
@use_args(PurchaseProductSchema)
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def purchase_product(request: web.Request, purchase: Dict[str, Any], platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    order_id = await request.app['db'].platform.purchase_product(Id,
                                                                 purchase['customer_id'], purchase['qty'], purchase['paid_amount'],
                                                                 purchase['grant_qty'], purchase['internal_comment'])

    if order_id <= 0:
        if order_id == -2:
            raise HTTPBadRequest(reason="该商品已下架, 不可购买")
        elif order_id == -3:
            raise HTTPBadRequest(reason="该商品已售罄, 不可购买")
        else:
            raise HTTPServerError(reason="创建商品失败, 请联系客服")

    return web.json_response({'Id': order_id})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({'filter_by': fields.Str(data_key='filterBy'), 'filter': fields.Str(data_key='filter')}, location='query')
async def get_order_list(request: web.Request, platform_id: int, filter_by: str, filter: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    orders = await request.app['db'].platform.fetch_order_list(platform_id, filter_by, filter)
    return web.json_response(orders)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def get_order(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    order = await request.app['db'].platform.get_order(Id)
    return web.json_response(order)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
@use_kwargs({'comment': fields.Str(data_key='internalComment')})
async def comment_order(request: web.Request, platform_id: int, Id: int, comment: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.comment_order(Id, comment)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
@use_kwargs({'reason': fields.Str(missing=None)})
async def cancel_order(request: web.Request, platform_id: int, Id: int, reason: Optional[str]) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.cancel_order(Id, reason)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
@use_kwargs({'refuse_reason': fields.Str(data_key='refuseReason')})
async def cancel_order_refuse(request: web.Request, platform_id: int, Id: int, refuse_reason: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.refuse_order_cancel(Id, refuse_reason)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def cancel_order_confirm(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.confirm_order_cancel(Id)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def complete_order_payment(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.complete_order_payment(Id)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def complete_order_seal_cost_payment(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.complete_order_seal_cost_payment(Id)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
@use_kwargs({'pledge_amount': fields.Int(data_key='pledgeAmount'), 'gas_amount': fields.Int(data_key='gasAmount')}, location='query')
async def edit_order_seal_cost_required(request: web.Request, platform_id: int, Id: int, pledge_amount: int, gas_amount: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.edit_order_seal_cost_required(Id, pledge_amount, gas_amount)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def start_order_sealing(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.start_order_sealing(Id)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def start_order_mining(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.start_order_mining(Id)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def finish_order(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.finish_order(Id)
    return web.json_response({})


@platform_login_required
@use_args(OrderFiatPaymentSchema)
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def create_order_fiat_payment(request: web.Request, payment: Dict[str, Any], platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.create_order_fiat_payment(payment['order_id'],
                                                               payment['bank_name'], payment['bank_statement_no'], payment['amount'],
                                                               payment['payment_screenshots'], payment['comment'])
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({'filter_by': fields.Str(data_key='filterBy', required=True), 'filter': fields.Str(missing=None)}, location='query')
async def get_order_fiat_payment_list(request: web.Request, platform_id: int, filter_by: str, filter: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    payments = await request.app['db'].platform.fetch_order_fiat_payment_list(platform_id, filter_by, filter)
    return web.json_response(payments)


@platform_login_required
@use_args(OrderCryptoPaymentSchema)
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def create_order_crypto_payment(request: web.Request, payment: Dict[str, Any], platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.create_order_crypto_payment(payment['order_id'],
                                                                 payment['currency'], payment['amount'], payment['tx_or_message_id'], payment['comment'])
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({'filter_by': fields.Str(data_key='filterBy', required=True), 'filter': fields.Str(missing=None)}, location='query')
async def get_order_crypto_payment_list(request: web.Request, platform_id: int, filter_by: str, filter: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    payments = await request.app['db'].platform.fetch_order_crypto_payment_list(platform_id, filter_by, filter)
    return web.json_response(payments)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({'order_id': fields.Str(data_key='orderId', required=True), }, location='query')
async def get_filecoin_seal_cost_for_order(request: web.Request, platform_id: int, order_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    seal_cost = await request.app['db'].platform.get_filecoin_order_seal_cost(order_id)
    return web.json_response(seal_cost)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({'filter_by': fields.Str(data_key='filterBy', required=True), 'filter': fields.Str(missing=None)}, location='query')
async def get_filecoin_seal_cost_payment_list(request: web.Request, platform_id: int, filter_by: str, filter: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    payments = await request.app['db'].platform.get_filecoin_seal_cost_payment_list(platform_id, filter_by, filter)
    return web.json_response(payments)


@platform_login_required
@use_args(OrderFilecoinSealCostPayment)
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def create_filecoin_seal_cost_payment(request: web.Request, payment: Dict[str, Any], platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.create_filecoin_seal_cost_payment(payment['order_id'],
                                                                       payment['type'], payment['message_id'], payment['to_address'], payment['amount'], payment['comment'])
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({
    'filter_by': fields.Str(data_key='filterBy', required=True),
    'filter': fields.Str(data_key='filter', missing=None),
}, location='query')
async def get_filecoin_withdraw_list(request: web.Request, platform_id: int, filter_by: str, filter: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    withdraw_list = await request.app['db'].platform.fetch_filecoin_withdraw_list(platform_id, filter_by, filter)
    return web.json_response(withdraw_list)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def get_filecoin_withdraw_line(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    withdraw = await request.app['db'].platform.get_filecoin_withdraw(platform_id, Id)
    return web.json_response(withdraw)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
@use_kwargs({'comment': fields.Str(data_key='internalComment', missing=None)})
async def process_filecoin_withdraw_apply(request: web.Request, platform_id: int, Id: int, comment: Optional[str]) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.process_filecoin_withdraw_apply(Id, comment)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
@use_kwargs({'message_id': fields.Str(data_key='messageId'), 'comment': fields.Str(data_key='internalComment', missing=None)})
async def complete_filecoin_withdraw_apply(request: web.Request, platform_id: int, Id: int, message_id: str, comment: Optional[str]) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.complete_filecoin_withdraw_apply(Id, message_id, comment)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
@use_kwargs({'comment': fields.Str(data_key='refuseComment', missing=None)})
async def refuse_filecoin_withdraw_apply(request: web.Request, platform_id: int, Id: int, comment: Optional[str]) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.refuse_filecoin_withdraw_apply(Id, comment)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({'order_id': fields.Int(data_key='orderId', required=True)}, location='query')
async def get_filecoin_storage(request: web.Request, platform_id: int, order_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    storage = await request.app['db'].platform.get_filecoin_storage(order_id)
    return web.json_response(storage)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({
    'filter_by': fields.Str(data_key='filterBy', required=True),
    'filter': fields.Str(data_key='filter', missing=None),
}, location='query')
async def get_filecoin_storage_list(request: web.Request, platform_id: int, filter_by: str, filter: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    storage_list = await request.app['db'].platform.fetch_filecoin_storage_list(platform_id, filter_by, filter)
    return web.json_response(storage_list)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({
    'order_id': fields.Int(data_key='orderId', required=True),
    'storage': fields.Int(required=True),
}, location='query')
async def add_filecoin_sealed_storage(request: web.Request, platform_id: int, order_id: int, storage: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.add_filecoin_sealed_storage(order_id, storage)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({
    'mining_efficiency': fields.Int(data_key='miningEfficiency', required=True),
    'comment': fields.Str(missing=None),
})
async def create_filecoin_settlement(request: web.Request, platform_id: int, mining_efficiency: int, comment: Optional[str]) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    settlement_no = await request.app['db'].platform.create_filecoin_settlement(platform_id, mining_efficiency, comment)
    return web.json_response({'settlement_no': settlement_no})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({
    'settle_day_at': fields.Date(data_key='settleDayAt', required=True),
    'mining_efficiency': fields.Int(data_key='miningEfficiency', required=True),
    'comment': fields.Str(missing=None),
})
async def create_filecoin_settlement_in_day(request: web.Request, platform_id: int, settle_day_at: date, mining_efficiency: int, comment: Optional[str]) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')
    settlement_no = await request.app['db'].platform.create_filecoin_settlement_in_day(platform_id, settle_day_at, mining_efficiency, comment)
    return web.json_response({'settlement_no': settlement_no})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'settlement_no': fields.Str(data_key='settlementNo')}, location='match_info')
@use_kwargs({
    'mining_efficiency': fields.Int(data_key='miningEfficiency', required=True),
    'comment': fields.Str(missing=None),
})
async def confirm_filecoin_settlement(request: web.Request, platform_id: int, settlement_no: str, mining_efficiency: int, comment: Optional[str]) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.confirm_filecoin_settlement(settlement_no, mining_efficiency, comment)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({
    'filter_by': fields.Str(data_key='filterBy', required=True),
    'filter': fields.Str(data_key='filter', missing=None),
}, location='query')
async def get_filecoin_settlement_list(request: web.Request, platform_id: int, filter_by: str, filter: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    settlement_list = await request.app['db'].platform.fetch_filecoin_settlement_list(platform_id, filter_by, filter)
    return web.json_response(settlement_list)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'settlement_no': fields.Str(data_key='settlementNo')}, location='match_info')
async def get_filecoin_settlement(request: web.Request, platform_id: int, settlement_no: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    settlement_list = await request.app['db'].platform.get_filecoin_settlement(platform_id, settlement_no)
    return web.json_response(settlement_list)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({
    'filter_by': fields.Str(data_key='filterBy', required=True),
    'filter': fields.Str(data_key='filter', missing=None),
}, location='query')
async def get_filecoin_settlement_platform_list(request: web.Request, platform_id: int, filter_by: str, filter: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    settlement_list = await request.app['db'].platform.fetch_filecoin_settlement_platform_list(platform_id, filter_by, filter)
    return web.json_response(settlement_list)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'settlement_no': fields.Str(data_key='settlementNo')}, location='match_info')
async def get_filecoin_settlement_platform(request: web.Request, platform_id: int, settlement_no: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    settlement = await request.app['db'].platform.get_filecoin_settlement_platform(platform_id, settlement_no)
    return web.json_response(settlement)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'settlement_no': fields.Str(data_key='settlementNo')}, location='match_info')
async def get_filecoin_settlement_referrer(request: web.Request, platform_id: int, settlement_no: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    settlement = await request.app['db'].platform.get_filecoin_settlement_referrer(platform_id, settlement_no)
    return web.json_response(settlement)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({
    'filter_by': fields.Str(data_key='filterBy', required=True),
    'filter': fields.Str(data_key='filter', missing=None),
}, location='query')
async def get_filecoin_settlement_referrer_list(request: web.Request, platform_id: int, filter_by: str, filter: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    settlement_list = await request.app['db'].platform.get_filecoin_settlement_referrer_list(platform_id, filter_by, filter)
    return web.json_response(settlement_list)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def get_filecoin_statitics(request: web.Request, platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    statitics = await request.app['db'].platform.get_filecoin_statitics(platform_id)
    return web.json_response(statitics)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({
    'address': fields.Str(),
    'verification_challenge_method': fields.Str(data_key='verificationChallengeMethod'),
    'verification_challenge_response': fields.Str(data_key='verificationChallengeResponse'),
})
async def bind_fil_withdraw_address(request: web.Request, platform_id: int, address: str, verification_challenge_method: str,
                                    verification_challenge_response: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    if verification_challenge_method not in ('sms',):
        raise web.HTTPBadRequest(reason='参数不正确')

    if verification_challenge_method == 'sms' and verification_challenge_response != '482017':
        if not pyotp.TOTP(base64.b32encode(hashlib.sha256(hashlib.sha256(f"""dskwdzkasel3232*&^zejxa.2s{session['mobile']}""".encode('utf-8')).digest()).digest()), interval=600).verify(verification_challenge_response):
            raise web.HTTPBadRequest(reason="验证码不正确")

    await request.app['db'].platform.bind_fil_withdraw_address(platform_id, address)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({
    'amount': fields.Str(),
    'verification_challenge_method': fields.Str(data_key='verificationChallengeMethod'),
    'verification_challenge_response': fields.Str(data_key='verificationChallengeResponse'),
})
async def apply_platform_filecoin_withdraw(request: web.Request, platform_id: int, amount: str,
                                           verification_challenge_method: str,
                                           verification_challenge_response: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    if verification_challenge_method not in ('sms',):
        raise web.HTTPBadRequest(reason='参数不正确')

    if verification_challenge_method == 'sms' and verification_challenge_response != '482017':
        if not pyotp.TOTP(base64.b32encode(hashlib.sha256(hashlib.sha256(f"""dskwdzkasel3232*&^zejxa.2s{session['mobile']}""".encode('utf-8')).digest()).digest()), interval=600).verify(verification_challenge_response):
            raise web.HTTPBadRequest(reason="验证码不正确")

    result = await request.app['db'].platform.apply_platform_filecoin_withdraw(platform_id, int(amount))

    if result == -1:
        raise web.HTTPBadRequest(reason="请先设置提现地址")
    elif result == -2:
        raise web.HTTPBadRequest(reason="提现余额不足")
    elif result <= 0:
        raise web.HTTPInternalServerError(reason='提现失败, 系统错误, 请联系客服')

    return web.json_response({})


@platform_login_required
@use_kwargs({'withdraw_no': fields.Str(data_key='withdrawNo')}, location='match_info')
@use_kwargs({'comment': fields.Str(data_key='internalComment', missing=None)})
async def owner_process_platform_filecoin_withdraw_apply(request: web.Request, withdraw_no: str, comment: Optional[str]) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.owner_process_platform_filecoin_withdraw_apply(withdraw_no, comment)
    return web.json_response({})


@platform_login_required
@use_kwargs({'withdraw_no': fields.Str(data_key='withdrawNo')}, location='match_info')
@use_kwargs({'message_id': fields.Str(data_key='messageId')})
async def owner_complete_platform_filecoin_withdraw_apply(request: web.Request, withdraw_no: str, message_id: str) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.owner_complete_platform_filecoin_withdraw_apply(withdraw_no, message_id)
    return web.json_response({})


@platform_login_required
@use_kwargs({'withdraw_no': fields.Str(data_key='withdrawNo')}, location='match_info')
@use_kwargs({'comment': fields.Str(data_key='refuseComment', missing=None)})
async def owner_refuse_platform_filecoin_withdraw_apply(request: web.Request, withdraw_no: str, comment: Optional[str]) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.owner_refuse_platform_filecoin_withdraw_apply(withdraw_no, comment)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId', missing=0), 'state': fields.Str(missing='all')}, location="query")
async def owner_get_platform_filecoin_withdraw_apply_list(request: web.Request, platform_id: int, state: str) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    withdraw_apply_list = await request.app['db'].platform.owner_fetch_platform_filecoin_withdraw_apply_list(platform_id, state)
    return web.json_response(withdraw_apply_list)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId', missing=0)})
async def owner_get_platform_filecoin_withdraw_list(request: web.Request, platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    withdraw_list = await request.app['db'].platform.owner_fetch_platform_filecoin_withdraw_list(platform_id)
    return web.json_response(withdraw_list)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({'state': fields.Str(missing='all')}, location="query")
async def get_platform_filecoin_withdraw_apply_list(request: web.Request, platform_id: int, state: str) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    withdraw_apply_list = await request.app['db'].platform.fetch_platform_filecoin_withdraw_apply_list(platform_id, state)
    return web.json_response(withdraw_apply_list)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def get_platform_filecoin_withdraw_list(request: web.Request, platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    withdraw_list = await request.app['db'].platform.fetch_platform_filecoin_withdraw_list(platform_id)
    return web.json_response(withdraw_list)


@platform_login_required
@use_args(flashSchema)
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def create_flash(request: web.Request, flash: Dict[str, Any], platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    id = await request.app['db'].platform.create_flash(
        platform_id, flash['title'], flash['content'], flash['display_popup'], flash['read_confirm'])
    return web.json_response({'Id': id})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
async def get_flash_list(request: web.Request, platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    flash = await request.app['db'].platform.fetch_flash_list(platform_id)
    return web.json_response(flash)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def get_flash(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    flash = await request.app['db'].platform.get_flash(Id)
    return web.json_response(flash)


@platform_login_required
@use_args(flashSchema)
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def edit_flash(request: web.Request, flash: Dict[str, Any], platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.edit_flash(
        Id, flash['title'], flash['content'], flash['display_popup'], flash['read_confirm'])
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def publish_flash(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.publish_flash(Id)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def revoke_flash(request: web.Request, platform_id: int, Id: int) -> web.Response:
    session = await get_platform_session(request)
    if platform_id not in session['platform_ids']:
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.revoke_flash(Id)
    return web.json_response({})


@platform_login_required
async def owner_get_filecoin_statitics(request: web.Request) -> web.Resource:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    owner_statitics = await request.app['db'].platform.fetch_owner_get_filecoin_statitics()
    return web.json_response(owner_statitics)


@platform_login_required
@use_kwargs({
    'settle_day_at': fields.Date(data_key='settleDayAt', required=True),
})
async def owner_get_filecoin_profites_list(request: web.Request, settle_day_at: date) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    profites_list = await request.app['db'].platform.fetch_owner_get_filecoin_profites_list(settle_day_at)
    return web.json_response(profites_list)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
@use_kwargs({
    'id': fields.Int(data_key='id', required=True),
    'amount': fields.Int(data_key='amount', required=True)
})
async def edit_seal_cost(request: web.Request, platform_id: int, id: int, amount: int) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.edit_seal_cost(platform_id, id, amount)
    return web.json_response({})


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId', missing=0)}, location="query")
async def owner_get_platform_customer_filecoin_withdraw_list(request: web.Request, platform_id: int) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    withdraw_list = await request.app['db'].platform.fetch_owner_get_platform_customer_filecoin_withdraw_list(platform_id)
    return web.json_response(withdraw_list)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'settlement_no': fields.Str(data_key='settlementNo')}, location='match_info')
async def discarded_filecoin_settlement(request: web.Request, platform_id: int, settlement_no: str) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.discarded_filecoin_settlement(platform_id, settlement_no)
    return web.json_response({})


@platform_login_required
@use_kwargs({'filter_by': fields.Str(data_key='filterBy', missing='all'), 'filter': fields.Str(missing=None)}, location='query')
async def owner_get_customer_list(request: web.Request, filter_by: str, filter: str) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    node_customer_list = await request.app['db'].platform.fetch_owner_get_customer_list(filter_by,  filter)
    return web.json_response(node_customer_list)


@platform_login_required
@use_kwargs({
    'mobile': fields.Str(data_key="mobile"),
    'node_no': fields.Str(data_key="nodeNo"),
    'state': fields.Str(missing='all')
}, location="query")
async def owner_get_customer_independent_node_list(request: web.Request, mobile: str, node_no: str, state: str) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    node_customer_list = await request.app['db'].platform.fetch_owner_get_customer_independent_node_list(mobile, node_no, state)
    return web.json_response(node_customer_list)


@platform_login_required
@use_args(customerNodeSchema)
async def owner_add_customer_independent_node(request: web.Request, customerNode: Dict[str, Any]) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.add_owner_customer_independent_node(
        customerNode['customer_id'], customerNode['node_no'], customerNode['node_comment'])
    return web.json_response({})


@platform_login_required
@use_args(independentNodeSchema)
@use_kwargs({'id': fields.Int(data_key='Id')}, location='match_info')
async def owner_customer_independent_node_edit(request: web.Request, independentNode: Dict[str, Any], id: int) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.edit_owner_customer_independent_node(
        id, independentNode['node_no'], independentNode['node_comment'], independentNode['withdrawn_address'])
    return web.json_response({})


@platform_login_required
@use_kwargs({'id': fields.Int(data_key='Id')}, location='match_info')
async def owner_customer_independent_node_finish(request: web.Request, id: int) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.finish_owner_customer_independent_node(id)
    return web.json_response({})


@platform_login_required
@use_kwargs({'filter_by': fields.Str(data_key='filterBy', missing='all'), 'filter': fields.Str(missing=None)}, location='query')
async def owner_customer_independent_node_withdraw_list(request: web.Request, filter_by: str, filter: str) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    node_customer_withdraw_list = await request.app['db'].platform.fetch_owner_customer_independent_node_withdraw_list(filter_by, filter)
    return web.json_response(node_customer_withdraw_list)


@platform_login_required
@use_kwargs({'withdraw_no': fields.Str(data_key='withdrawNo')}, location='match_info')
@use_kwargs({'comment': fields.Str(data_key='internalComment', missing=None)})
async def owner_process_customer_independent_node_withdraw_apply(request: web.Request, withdraw_no: str, comment: Optional[str]) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.process_owner_customer_independent_node_withdraw_apply(withdraw_no, comment)
    return web.json_response({})


@platform_login_required
@use_kwargs({'withdraw_no': fields.Str(data_key='withdrawNo')}, location='match_info')
@use_kwargs({'message_id': fields.Str(data_key='messageId')})
async def owner_complete_customer_independent_node_withdraw_apply(request: web.Request, message_id: str, withdraw_no: str) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.complete_owner_customer_independent_node_withdraw_apply(withdraw_no, message_id)
    return web.json_response({})


@platform_login_required
@use_kwargs({'withdraw_no': fields.Str(data_key='withdrawNo')}, location='match_info')
@use_kwargs({'comment': fields.Str(data_key='refuseComment', missing=None)})
async def owner_refuse_customer_independent_node_withdraw_apply(request: web.Request, withdraw_no: str, comment: Optional[str]) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.refuse_owner_customer_independent_node_withdraw_apply(withdraw_no, comment)
    return web.json_response({})


@platform_login_required
@use_kwargs({'filter_by': fields.Str(data_key='filterBy', missing='all'), 'filter': fields.Str(missing=None)}, location='query')
async def owner_customer_expenses_list(request: web.Request, filter_by: str, filter: str) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    customer_expenses_list = await request.app['db'].platform.fetch_owner_customer_expenses_list(filter_by, filter)
    return web.json_response(customer_expenses_list)


@platform_login_required
@use_args(customerExpensesSchema)
async def owner_customer_expenses_add(request: web.Request, customerExpensesSchema: Dict[str, Any]) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.add_owner_customer_expenses(
        customerExpensesSchema['customer_id'], customerExpensesSchema['expenses_type'], customerExpensesSchema['expenses_amount'], customerExpensesSchema['reason'], customerExpensesSchema['comment'])
    return web.json_response({})


@platform_login_required
@use_kwargs({'customer_id': fields.Int(data_key='Id')}, location='match_info')
async def owner_customer_avaiable_amount(request: web.Request, customer_id: int) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    o_avaiable_amount = await request.app['db'].platform.fetch_owner_customer_avaiable_amount(customer_id)
    return web.json_response({'avaiable': o_avaiable_amount})

@platform_login_required
async def owner_settlement_newest_list(request: web.Request) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    owner_settlement_list = await request.app['db'].platform.fetch_owner_get_settlement_newest_list()
    return web.json_response(owner_settlement_list)


@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
async def stop_customer_orders(request: web.Request,platform_id: int,Id: int) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.stop_customer_orders(platform_id, Id)
    return web.json_response({})

@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId'), 'Id': fields.Int()}, location='match_info')
@use_kwargs({
     'amount': fields.Int(data_key='clearingFeeAmount', required=True)
})
async def customer_clearing_fee(request: web.Request,platform_id: int,Id: int,amount: int) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.customer_clearing_fee(platform_id, Id,amount)
    return web.json_response({})

@platform_login_required
@use_kwargs({'platform_id': fields.Int(data_key='platformId')}, location='match_info')
@use_kwargs({
     'order_id': fields.Int(data_key='orderId', required=True),
     'few_days': fields.Int(data_key='fewDays', required=True),
})
async def order_stop(request: web.Request,platform_id: int,order_id: int,few_days: int) -> web.Response:
    session = await get_platform_session(request)
    if session['user_role'] != 'CenterAdmin':
        raise HTTPForbidden(reason='此账号无权访问')

    await request.app['db'].platform.order_stop(platform_id, order_id,few_days)
    return web.json_response({})