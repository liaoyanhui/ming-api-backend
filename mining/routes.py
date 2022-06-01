from aiohttp import web

from .handlers import customer, platform, app_release


def setup_customer_routes(root: web.Application) -> web.Application:
    app = web.Application()
    app.router.add_post('/auth/signin/mobile', customer.mobile_signin)
    app.router.add_post('/auth/signout', customer.signout)

    app.router.add_post('/security/verification/sms/send',
                        customer.send_sms_verification)
    app.router.add_post(
        '/security/verification/pincode/bind', customer.bind_pincode)
    app.router.add_post('/security/withdraw/fil/address/bind',
                        customer.bind_fil_withdraw_address)

    app.router.add_post(
        '/referrer/bind', customer.bind_referrer_by_device_udid)

    app.router.add_get('/profile', customer.get_profile)

    app.router.add_get('/app/releases/latest', customer.get_latest_app_release)

    app.router.add_get('/filecoin/network', customer.get_filecoin_network)
    app.router.add_get('/currency/price/index',
                       customer.get_currency_price_index)

    app.router.add_get('/platform/notices/list',
                       customer.get_platform_notice_list)
    app.router.add_get(
        '/platform/notices/{Id:\d+}', customer.get_platform_notice)
    app.router.add_get(
        '/platform/agreements/{Id:\d+}', customer.get_platform_agreement)

    app.router.add_get('/products/list', customer.get_product_list)
    app.router.add_get('/products/{Id:\d+}', customer.get_product)
    app.router.add_post(
        '/products/{Id:\d+}/purchase', customer.purchase_product)

    app.router.add_get('/orders/list', customer.get_order_list)
    app.router.add_get('/orders/{Id:\d+}', customer.get_order)
    app.router.add_post('/orders/{Id:\d+}/cancel', customer.cancel_order)
    app.router.add_get(
        '/orders/{Id:\d+}/filecoin/seal/cost', customer.get_filecoin_order_seal_cost)

    app.router.add_get('/filecoin/seal/cost/payments/list',
                       customer.get_filecoin_seal_cost_payment_list)
    app.router.add_get('/filecoin/revenue/statitics',
                       customer.get_filecoin_revenue_statitics)
    app.router.add_post('/filecoin/withdraw/apply',
                        customer.apply_filecoin_withdraw)
    app.router.add_get('/filecoin/withdraw/list',
                       customer.get_filecoin_withdraw_list)
    app.router.add_get('/filecoin/settlement/list',
                       customer.get_filecoin_settlement_list)
    app.router.add_get('/filecoin/settlement/referrer/list',
                       customer.get_filecoin_settlement_referrer_list)

    app.router.add_post('/profile/edit', customer.edit_profile)

    app.router.add_get('/platform/flash/list',
                       customer.get_platform_flash_list)
    app.router.add_get(
        '/platform/flash/{Id:\d+}', customer.get_platform_flash)

    app.router.add_get(
        '/customer/independent/node/list', customer.get_customer_independent_node_list)

    app.router.add_post('/platform/flash/confirm/read/{Id:\d+}',
                        customer.flash_confirm_read)

    app.router.add_post('/customer/independent/node/{Id:\d+}/edit',
                        customer.customer_independent_node_edit)
    app.router.add_post('/customer/independent/node/withdraw/apply',
                        customer.apply_independent_node_withdraw)
    app.router.add_get('/customer/expense/list',
                       customer.get_customer_expense_list)

    return app


def setup_platform_routes(root: web.Application) -> web.Application:
    app = web.Application()
    app.router.add_post('/security/verification/sms/send',
                        platform.send_sms_verification)

    app.router.add_post('/auth/signin/mobile', platform.mobile_signin)
    app.router.add_post('/auth/signout', platform.signout)

    app.router.add_get('/filecoin/network', platform.get_filecoin_network)
    app.router.add_get('/filecoin/network/mining/efficiency',
                       platform.get_filecoin_mining_efficiency)

    app.router.add_post('/owner/platforms/create',
                        platform.owner_create_platform)
    app.router.add_post(
        '/owner/platforms/{Id:\d+}/customer/rebind', platform.owner_rebind_customer_to_platform)
    app.router.add_post(
        '/owner/platforms/{Id:\d+}/setting/edit', platform.owner_setting_platform)
    app.router.add_get('/owner/platforms/list',
                       platform.owner_get_platform_list)

    app.router.add_post('/owner/app/releases/create',
                        platform.owner_create_app_release)
    app.router.add_post(
        '/owner/app/releases/{Id:\d+}/edit', platform.owner_edit_app_release)
    app.router.add_post(
        '/owner/app/releases/{Id:\d+}/publish', platform.owner_app_release_publish)
    app.router.add_post(
        '/owner/app/releases/{Id:\d+}/revoke', platform.owner_app_release_revoke)
    app.router.add_post(
        '/owner/app/releases/{Id:\d+}/android/upload', platform.owner_upload_android_release_apk)
    app.router.add_get('/owner/app/releases/list',
                       platform.owner_fetch_app_release_list)

    app.router.add_post('/platforms/{Id:\d+}/edit', platform.edit_platform)
    app.router.add_get('/platforms/{Id:\d+}', platform.get_platform)

    app.router.add_get(
        '/platforms/{platformId:\d+}/agreements/list', platform.get_agreement_list)
    app.router.add_get(
        '/platforms/{platformId:\d+}/agreements/{Id:\d+}', platform.get_agreement)
    app.router.add_post(
        '/platforms/{platformId:\d+}/agreements/create', platform.create_agreement)
    app.router.add_post(
        '/platforms/{platformId:\d+}/agreements/{Id:\d+}/edit', platform.edit_agreement)

    app.router.add_get(
        '/platforms/{platformId:\d+}/notices/{Id:\d+}', platform.get_notice)
    app.router.add_get(
        '/platforms/{platformId:\d+}/notices/list', platform.get_notice_list)
    app.router.add_post(
        '/platforms/{platformId:\d+}/notices/create', platform.create_notice)
    app.router.add_post(
        '/platforms/{platformId:\d+}/notices/{Id:\d+}/edit', platform.edit_notice)
    app.router.add_post(
        '/platforms/{platformId:\d+}/notices/{Id:\d+}/publish', platform.publish_notice)
    app.router.add_post(
        '/platforms/{platformId:\d+}/notices/{Id:\d+}/revoke', platform.revoke_notice)

    app.router.add_post(
        '/platforms/{platformId:\d+}/albums/create', platform.create_albums)
    app.router.add_post(
        '/platforms/{platformId:\d+}/photos/{Id:\d+}', platform.get_photo)
    app.router.add_post(
        '/platforms/{platformId:\d+}/photos/{Id:\d+}/delete', platform.remove_photo)
    app.router.add_post(
        '/platforms/{platformId:\d+}/photos/upload', platform.upload_photo)

    app.router.add_get(
        '/platforms/{platformId:\d+}/customers/{Id:\d+}', platform.get_customer)
    app.router.add_post(
        '/platforms/{platformId:\d+}/customers/create', platform.create_customer)
    app.router.add_post(
        '/platforms/{platformId:\d+}/customers/{Id:\d+}/referrer/rebind', platform.rebind_customer_referrer)
    app.router.add_post(
        '/platforms/{platformId:\d+}/customers/{Id:\d+}/edit', platform.edit_customer)
    app.router.add_get(
        '/platforms/{platformId:\d+}/customers/list', platform.get_customer_list)

    app.router.add_get(
        '/platforms/{platformId:\d+}/referrer/list', platform.get_referrer_list)
    app.router.add_get(
        '/platforms/{platformId:\d+}/referrer/{Id:\d+}', platform.get_referrer)
    app.router.add_get(
        '/platforms/{platformId:\d+}/referrer/{Id:\d+}/customer/list', platform.get_referrer_customer_list)
    app.router.add_post(
        '/platforms/{platformId:\d+}/referrer/{Id:\d+}/commission', platform.set_referrer_commission)

    app.router.add_post(
        '/platforms/{platformId:\d+}/products/create', platform.create_product)
    app.router.add_get(
        '/platforms/{platformId:\d+}/products/list', platform.get_product_list)
    app.router.add_get(
        '/platforms/{platformId:\d+}/products/{Id:\d+}', platform.get_product)
    app.router.add_post(
        '/platforms/{platformId:\d+}/products/{Id:\d+}/edit', platform.edit_product)
    app.router.add_post(
        '/platforms/{platformId:\d+}/products/{Id:\d+}/state/change', platform.change_product_state)
    app.router.add_post(
        '/platforms/{platformId:\d+}/products/{Id:\d+}/purchase', platform.purchase_product)

    app.router.add_get(
        '/platforms/{platformId:\d+}/orders/{Id:\d+}', platform.get_order)
    app.router.add_get(
        '/platforms/{platformId:\d+}/orders/list', platform.get_order_list)
    app.router.add_post(
        '/platforms/{platformId:\d+}/orders/{Id:\d+}/comment', platform.comment_order)
    app.router.add_post(
        '/platforms/{platformId:\d+}/orders/{Id:\d+}/cancel', platform.cancel_order)
    app.router.add_post(
        '/platforms/{platformId:\d+}/orders/{Id:\d+}/cancel/refuse', platform.cancel_order_refuse)
    app.router.add_post(
        '/platforms/{platformId:\d+}/orders/{Id:\d+}/cancel/confirm', platform.cancel_order_confirm)
    app.router.add_post(
        '/platforms/{platformId:\d+}/orders/{Id:\d+}/sale/payment/complete', platform.complete_order_payment)
    app.router.add_post(
        '/platforms/{platformId:\d+}/orders/{Id:\d+}/seal/cost/payment/complete', platform.complete_order_seal_cost_payment)
    app.router.add_post(
        '/platforms/{platformId:\d+}/orders/{Id:\d+}/seal/cost/edit', platform.edit_order_seal_cost_required)
    app.router.add_post(
        '/platforms/{platformId:\d+}/orders/{Id:\d+}/sealing/start', platform.start_order_sealing)
    app.router.add_post(
        '/platforms/{platformId:\d+}/orders/{Id:\d+}/mining/start', platform.start_order_mining)
    app.router.add_post(
        '/platforms/{platformId:\d+}/orders/{Id:\d+}/finish', platform.finish_order)

    app.router.add_post(
        '/platforms/{platformId:\d+}/payment/order/fiat/create', platform.create_order_fiat_payment)
    app.router.add_get(
        '/platforms/{platformId:\d+}/payment/order/fiat/list', platform.get_order_fiat_payment_list)
    app.router.add_post(
        '/platforms/{platformId:\d+}/payment/order/crypto/create', platform.create_order_crypto_payment)
    app.router.add_get(
        '/platforms/{platformId:\d+}/payment/order/crypto/list', platform.get_order_crypto_payment_list)
    app.router.add_get('/platforms/{platformId:\d+}/payment/order/filecoin/seal/cost',
                       platform.get_filecoin_seal_cost_for_order)
    app.router.add_post(
        '/platforms/{platformId:\d+}/payment/order/filecoin/seal/cost/create', platform.create_filecoin_seal_cost_payment)
    app.router.add_get('/platforms/{platformId:\d+}/payment/order/filecoin/seal/cost/list',
                       platform.get_filecoin_seal_cost_payment_list)

    app.router.add_get(
        '/platforms/{platformId:\d+}/filecoin/withdraw/list', platform.get_filecoin_withdraw_list)
    app.router.add_get(
        '/platforms/{platformId:\d+}/filecoin/withdraw/{Id:\d+}', platform.get_filecoin_withdraw_line)
    app.router.add_post(
        '/platforms/{platformId:\d+}/filecoin/withdraw/{Id:\d+}/process', platform.process_filecoin_withdraw_apply)
    app.router.add_post(
        '/platforms/{platformId:\d+}/filecoin/withdraw/{Id:\d+}/complete', platform.complete_filecoin_withdraw_apply)
    app.router.add_post(
        '/platforms/{platformId:\d+}/filecoin/withdraw/{Id:\d+}/refuse', platform.refuse_filecoin_withdraw_apply)

    app.router.add_get(
        '/platforms/{platformId:\d+}/filecoin/storage', platform.get_filecoin_storage)
    app.router.add_get(
        '/platforms/{platformId:\d+}/filecoin/storage/list', platform.get_filecoin_storage_list)
    app.router.add_get(
        '/platforms/{platformId:\d+}/filecoin/storage/sealed/add', platform.add_filecoin_sealed_storage)

    app.router.add_post(
        '/platforms/{platformId:\d+}/filecoin/settlement/create', platform.create_filecoin_settlement)
    app.router.add_post(
        '/platforms/{platformId:\d+}/filecoin/settlement/day/create', platform.create_filecoin_settlement_in_day)
    app.router.add_post(
        '/platforms/{platformId:\d+}/filecoin/settlement/{settlementNo}/confirm', platform.confirm_filecoin_settlement)

    app.router.add_get(
        '/platforms/{platformId:\d+}/filecoin/settlement/list', platform.get_filecoin_settlement_list)
    app.router.add_get(
        '/platforms/{platformId:\d+}/filecoin/settlement/{settlementNo}', platform.get_filecoin_settlement)

    app.router.add_get('/platforms/{platformId:\d+}/filecoin/settlement/platform/list',
                       platform.get_filecoin_settlement_platform_list)
    app.router.add_get('/platforms/{platformId:\d+}/filecoin/settlement/{settlementNo}/platform',
                       platform.get_filecoin_settlement_platform)

    app.router.add_get('/platforms/{platformId:\d+}/filecoin/settlement/{settlementNo}/refferrer',
                       platform.get_filecoin_settlement_referrer)
    app.router.add_get('/platforms/{platformId:\d+}/filecoin/settlement/refferrer/list',
                       platform.get_filecoin_settlement_referrer_list)

    app.router.add_get(
        '/platforms/{platformId:\d+}/filecoin/statitics', platform.get_filecoin_statitics)

    app.router.add_post(
        '/platforms/{platformId:\d+}/security/withdraw/fil/address/bind', platform.bind_fil_withdraw_address)
    app.router.add_post(
        '/platforms/{platformId:\d+}/filecoin/withdraw/platform/apply', platform.apply_platform_filecoin_withdraw)

    app.router.add_post('/owner/filecoin/withdraw/{withdrawNo}/process',
                        platform.owner_process_platform_filecoin_withdraw_apply)
    app.router.add_post('/owner/filecoin/withdraw/{withdrawNo}/complete',
                        platform.owner_complete_platform_filecoin_withdraw_apply)
    app.router.add_post(
        '/owner/filecoin/withdraw/{withdrawNo}/refuse', platform.owner_refuse_platform_filecoin_withdraw_apply)

    app.router.add_get('/owner/filecoin/withdraw/apply/list',
                       platform.owner_get_platform_filecoin_withdraw_apply_list)
    app.router.add_get('/owner/filecoin/withdraw/list',
                       platform.owner_get_platform_filecoin_withdraw_list)

    app.router.add_get('/platforms/{platformId:\d+}/filecoin/withdraw/platform/apply/list',
                       platform.get_platform_filecoin_withdraw_apply_list)
    app.router.add_get('/platforms/{platformId:\d+}/filecoin/withdraw/platform/list',
                       platform.get_platform_filecoin_withdraw_list)
    app.router.add_get(
        '/owner/platforms/filecoin/statitics', platform.owner_get_filecoin_statitics)

    app.router.add_post(
        '/platforms/{platformId:\d+}/flash/create', platform.create_flash)
    app.router.add_get(
        '/platforms/{platformId:\d+}/flash/list', platform.get_flash_list)
    app.router.add_get(
        '/platforms/{platformId:\d+}/flash/{Id:\d+}', platform.get_flash)
    app.router.add_post(
        '/platforms/{platformId:\d+}/flash/{Id:\d+}/edit', platform.edit_flash)
    app.router.add_post(
        '/platforms/{platformId:\d+}/flash/{Id:\d+}/publish', platform.publish_flash)
    app.router.add_post(
        '/platforms/{platformId:\d+}/flash/{Id:\d+}/revoke', platform.revoke_flash)

    app.router.add_post(
        '/owner/filecoin/profites/list', platform.owner_get_filecoin_profites_list)
    app.router.add_post(
        '/platforms/{platformId:\d+}/filecoin/seal/cost/edit', platform.edit_seal_cost)

    app.router.add_get('/owner/filecoin/customer/withdraw/list',
                       platform.owner_get_platform_customer_filecoin_withdraw_list)

    app.router.add_get(
        '/platforms/{platformId:\d+}/filecoin/settlement/{settlementNo}/discarded', platform.discarded_filecoin_settlement)

    app.router.add_get(
        '/owner/platforms/customers/list', platform.owner_get_customer_list)
    app.router.add_get(
        '/owner/customer/independent/node/list', platform.owner_get_customer_independent_node_list)
    app.router.add_post(
        '/owner/customer/independent/node/add', platform.owner_add_customer_independent_node)
    app.router.add_post(
        '/owner/customer/independent/node/{Id:\d+}/edit', platform.owner_customer_independent_node_edit)
    app.router.add_get(
        '/owner/customer/independent/node/{Id:\d+}/finish', platform.owner_customer_independent_node_finish)

    app.router.add_get('/owner/customer/independent/node/withdraw/list',
                       platform.owner_customer_independent_node_withdraw_list)

    app.router.add_post('/owner/customer/independent/node/withdraw/{withdrawNo}/process',
                        platform.owner_process_customer_independent_node_withdraw_apply)
    app.router.add_post('/owner/customer/independent/node/withdraw/{withdrawNo}/complete',
                        platform.owner_complete_customer_independent_node_withdraw_apply)
    app.router.add_post(
        '/owner/customer/independent/node/withdraw/{withdrawNo}/refuse', platform.owner_refuse_customer_independent_node_withdraw_apply)

    app.router.add_get('/owner/customer/expenses/list',
                       platform.owner_customer_expenses_list)
    app.router.add_post('/owner/customer/expenses/add',
                        platform.owner_customer_expenses_add)
    app.router.add_get('/owner/customer/avaiable/{Id:\d+}',
                       platform.owner_customer_avaiable_amount)

    app.router.add_get('/owner/settlement/newest/list',platform.owner_settlement_newest_list)

    app.router.add_get('/platforms/{platformId:\d+}/filecoin/customer/{Id:\d+}/stop',platform.stop_customer_orders)
    app.router.add_post('/platforms/{platformId:\d+}/filecoin/customer/{Id:\d+}/clearing/fee',platform.customer_clearing_fee)
    app.router.add_post('/platforms/{platformId:\d+}/filecoin/order/stop', platform.order_stop)
    
    return app


def setup_app_release_routes(root: web.Application) -> web.Application:
    app = web.Application()
    app.router.add_get('/release/{releaseId}/android/download/{fileName}',
                       app_release.download_android_release_apk_file)
    app.router.add_post('/preinstall/device/enroll',
                        app_release.enroll_preinstall_app_device)
    return app
