import io
import json
import time
from datetime import date
from typing import Any, Dict, List, Optional, Tuple
import psycopg2
import psycopg2.extras
from aiopg import create_pool, Pool
from aiohttp import web
from decimal import *


class Database:
    def __init__(self, db: Pool):
        self.db = db
        self.customer = self.Customer(self.db)
        self.platform = self.Platform(self.db)

    @classmethod
    async def create(cls, app):
        dsn = f"""dbname={app['config']['postgres']['database']} host={app['config']['postgres']['host']} port={app['config']['postgres']['port']}"""
        # dsn = f"""dbname={app['config']['postgres']['database']} user={app['config']['postgres']['user']}  password={app['config']['postgres']['password']} host={app['config']['postgres']['host']} port={app['config']['postgres']['port']}"""
        return cls(await create_pool(dsn))

    async def close(self, *args):
        self.db.close()
        await self.db.wait_closed()

    async def update_filecoin_network_info(self, info: Dict[str, Any]):
        async with self.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT yj_update_filecoin_network_info(%s)", (json.dumps(info), ))

    async def get_filecoin_network_info(self) -> Optional[Dict[str, Any]]:
        async with self.db.acquire() as conn:
            async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                await cur.execute("SELECT o_network_info from yj_get_filecoin_network_info()")
                result = await cur.fetchone()
                return result['o_network_info'] if result else None

    async def get_filecoin_mining_efficiency(self, day_at: date) -> Optional[Dict[str, Any]]:
        async with self.db.acquire() as conn:
            async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                await cur.execute("SELECT yj_get_filecoin_mining_efficiency(%s) as o_mining_efficiency", (day_at, ))
                result = await cur.fetchone()
                return result['o_mining_efficiency'] if result else None

    async def get_android_release_apk(self, release_id: int, file_name: str) -> Optional[memoryview]:
        async with self.db.acquire() as conn:
            async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                await cur.execute("select package from yj_android_app_release_package where app_release_id = %s AND package_file_name = %s", (release_id, file_name))
                result = await cur.fetchone()
                return result['package'] if result else None

    async def get_lastest_android_app_release(self) -> Tuple[int, str, memoryview]:
        async with self.db.acquire() as conn:
            async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                await cur.execute("select o_release_id, o_file_name, o_apk from yj_get_latest_android_app_release()")
                result = await cur.fetchone()
                return result['o_release_id'], result['o_file_name'], result['o_apk']

    async def enroll_preinstall_app_device(self, referral_code: str, device_udid: str):
        async with self.db.acquire() as conn:
            async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                await cur.execute("select yj_enroll_preinstall_app_device(%s, %s)", (referral_code, device_udid))

    async def load_session(self, id: str, is_customer: bool = True) -> Optional[Dict[str, any]]:
        async with self.db.acquire() as conn:
            async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                await cur.execute("SELECT o_session FROM yj_load_session(%s, %s)", (id, is_customer))
                result = await cur.fetchone()
                return result['o_session']

    async def save_session(self, id: str, user_id: int, session: str, max_age: int, is_customer: bool = True) -> None:
        async with self.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT yj_save_session(%s, %s, %s, %s, to_timestamp(%s))", (id, is_customer, user_id, session, int(time.time() + max_age)))

    class Customer:
        def __init__(self, db: Pool):
            self.db = db

        async def mobile_signin(self, mobile: str, nick_name: Optional[str] = None, referral_code: Optional[str] = None) -> Optional[Tuple[int, int, bool]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_customer_id, o_platform_id, o_first_signin from yj_customer_mobile_signin(%s, %s, %s)", (mobile, nick_name, referral_code))
                    result = await cur.fetchone()
                    return (result['o_customer_id'], result['o_platform_id'], result['o_first_signin']) if result else None

        async def signout(self, session_id: str):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_customer_signout(%s)", (session_id,))

        async def rebind_referral_code_by_device_udid(self, customer_id: int, in_device_udid: str):
            async with self.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("select yj_customer_rebind_referral_code_by_device_udid(%s, %s)", (customer_id, in_device_udid))

        async def pincode_verify(self, customer_id: int, pincode: str) -> bool:
            async with self.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("select yj_customer_pincode_verify(%s, %s)", (customer_id, pincode))
                    result = await cur.fetchone()
                    return result[0]

        async def bind_pincode(self, customer_id: int, pincode: str):
            async with self.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("select yj_customer_bind_pincode(%s, %s)", (customer_id, pincode))

        async def bind_fil_withdraw_address(self, customer_id: int, address: str):
            async with self.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("select yj_customer_bind_file_withdraw_address(%s, %s)", (customer_id, address))

        async def edit_profile(self, id: int, nickname: str, ):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_customer_edit(%s, %s)", (id, nickname))

        async def get_profile(self, customer_id: int) -> Dict[str, any]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_profile from yj_customer_get_profile(%s)", (customer_id,))
                    result = await cur.fetchone()
                    return result['o_profile']

        async def get_latest_app_release(self, platform: str) -> Optional[Dict[str, any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_release from yj_get_latest_app_release(%s)", (platform,))
                    result = await cur.fetchone()
                    return result['o_release']

        async def get_fetch_notice_list(self, platform_id: int, customer_id: int) -> Optional[List[Dict[str, Any]]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_notice_list from yj_customer_fetch_notice_list(%s, %s)", (platform_id, customer_id))
                    result = await cur.fetchone()
                    return result['o_notice_list'] if result else None

        async def get_notice(self, customer_id: int, notice_id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_notice from yj_customer_get_notice(%s, %s)", (customer_id, notice_id))
                    result = await cur.fetchone()
                    return result['o_notice'] if result else None

        async def get_agreement(self, agreement_id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_agreement from yj_get_agreement(%s)", (agreement_id,))
                    result = await cur.fetchone()
                    return result['o_agreement'] if result else None

        async def get_product_list(self, platform_id: int) -> Optional[List[Dict[str, Any]]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_product_list from yj_customer_fetch_product_list(%s)", (platform_id,))
                    result = await cur.fetchone()
                    return result['o_product_list'] if result else None

        async def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_product from yj_customer_get_product(%s)", (product_id,))
                    result = await cur.fetchone()
                    return result['o_product'] if result else None

        async def purchase_product(self, product_id: int, customer_id: int, qty: int, comment: Optional[str] = None) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("select yj_customer_product_purchase(%s, %s, %s, %s)", (product_id, customer_id, qty, comment))
                    result = await cur.fetchone()
                    return result[0]

        async def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_order from yj_customer_get_order(%s)", (order_id, ))
                    result = await cur.fetchone()
                    return result['o_order'] if result else None

        async def get_order_list(self, customer_id: int) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_order_list from yj_customer_fetch_order_list(%s)", (customer_id, ))
                    result = await cur.fetchone()
                    return result['o_order_list']

        async def cancel_order(self, order_id: int, reason: Optional[str] = None):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_customer_order_cancel(%s, %s)", (order_id, reason))

        async def get_filecoin_order_seal_cost(self, order_id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_seal_cost from yj_get_filecoin_order_seal_cost(%s)", (order_id,))
                    result = await cur.fetchone()
                    return result['o_seal_cost'] if result else None

        async def get_filecoin_seal_cost_payment_list(self, customer_id: int, order_id: Optional[int] = None) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_payment_list from yj_customer_fetch_filecoin_seal_cost_payment_list(%s, %s)", (customer_id, order_id,))
                    result = await cur.fetchone()
                    return result['o_payment_list'] if result else None

        async def apply_filecoin_withdraw(self, platform_id: int, customer_id: int, amount: int) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_withdraw_id from yj_customer_filecoin_withdraw_apply(%s, %s, %s)", (platform_id, customer_id, amount))
                    result = await cur.fetchone()
                    return result['o_withdraw_id']

        async def get_filecoin_withdraw_list(self, customer_id: int, state: Optional[str] = None) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_withdraw_list from yj_customer_fetch_filecoin_withdraw_list(%s, %s)", (customer_id, state))
                    result = await cur.fetchone()
                    return result['o_withdraw_list']

        async def get_filecoin_settlement_list(self, customer_id: int) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_settlement_list from yj_filecoin_customer_settlement_fetch_list(%s)", (customer_id,))
                    result = await cur.fetchone()
                    return result['o_settlement_list']

        async def get_filecoin_settlement_referrer_list(self, customer_id: int) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_settlement_list from yj_filecoin_customer_settlement_fetch_referrer_list(%s)", (customer_id,))
                    result = await cur.fetchone()
                    return result['o_settlement_list']

        async def get_filecoin_revenue_statitics(self, customer_id: int) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_revenue_statitics from yj_customer_filecoin_revenue_statitics(%s)", (customer_id,))
                    result = await cur.fetchone()
                    return result['o_revenue_statitics']

        async def get_fetch_flash_list(self, platform_id: int, customer_id: int) -> Optional[List[Dict[str, Any]]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_flash_list from yj_customer_fetch_flash_list(%s, %s)", (platform_id, customer_id))
                    result = await cur.fetchone()
                    return result['o_flash_list'] if result else None

        async def get_flash(self, customer_id: int, flash_id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_flash from yj_customer_get_flash(%s, %s)", (customer_id, flash_id))
                    result = await cur.fetchone()
                    return result['o_flash'] if result else None

        async def flash_confirm_read(self, customer_id: int, flash_id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("select yj_customer_flash_read(%s, %s)", (customer_id, flash_id))

        async def edit_customer_independent_node(self, id: int, withdrawn_address: str):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_customer_independent_node_edit(%s, %s)", (id, withdrawn_address))

        async def apply_independent_node_withdraw(self, customer_id: int, amount: int, node_id) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_withdraw_id from yj_customer_independent_node_withdraw_apply(%s, %s, %s)", (customer_id, amount, node_id))
                    result = await cur.fetchone()
                    return result['o_withdraw_id']

        async def get_customer_independent_node_list(self, customer_id: int, state: str) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_customer_node_list from yj_customer_independent_node_list(%s,%s)", (customer_id, state))
                    result = await cur.fetchone()
                    return result['o_customer_node_list'] if result else None

        async def get_customer_expense_list(self, customer_id: int, filter_by: str, filter: str) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_customer_expense_list from get_customer_filcoin_expense_list(%s,%s,%s)", (customer_id, filter_by, filter))
                    result = await cur.fetchone()
                    return result['o_customer_expense_list'] if result else None

    class Platform:
        def __init__(self, db: Pool):
            self.db = db

        async def mobile_signin(self, mobile: str) -> Tuple[int, Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_status_code, o_result from yj_platform_mobile_signin(%s)", (mobile,))
                    result = await cur.fetchone()
                    return (result['o_status_code'], result['o_result'])

        async def owner_create_platform(self, name: str, is_self_operated: bool, is_demo_platform: bool, intro: Optional[str] = None, language: Optional[str] = None, settings: Optional[str] = None) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_platform_id from yj_owner_create_platform(%s, %s, %s, %s,%s, %s)", (name, is_self_operated, is_demo_platform, intro, language, settings))
                    result = await cur.fetchone()
                    return result['o_platform_id']

        async def owner_create_app_release(self, version: str, platform: str, release_notes: str, download_url: str, comment: str):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_create_app_release(%s, %s, %s, %s, %s)", (version, platform, release_notes, download_url, comment))

        async def owner_edit_app_release(self, id: int, version: str, platform: str, release_notes: str, download_url: str, comment: str):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_edit_app_release(%s, %s, %s, %s, %s, %s)", (id, version, platform, release_notes, download_url, comment))

        async def owner_app_release_publish(self, id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_publish_app_release(%s)", (id, ))

        async def owner_app_release_revoke(self, id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_revoke_published_app_release(%s)", (id, ))

        async def owner_upload_android_release_apk(self, release_id: int, file_name: str, file: io.BufferedReader):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_upload_anroid_release_package(%s, %s, %s)", (release_id, file_name, psycopg2.Binary(file.read())))

        async def owner_fetch_app_release_list(self) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_release_list FROM yj_fetch_app_release_list()")
                    result = await cur.fetchone()
                    return result['o_release_list']

        async def owner_rebind_customer_to_platform(self, Id: int, customer_id: int, new_platform_id) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_owner_rebind_customer_to_platform(%s, %s, %s)", (Id, customer_id, new_platform_id))

        async def owner_setting_platform(self, id: int, is_self_operated: bool, is_demo_platform: bool, language: str, value: str):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_owner_setting_platform(%s, %s, %s,%s, %s)", (id, is_self_operated, is_demo_platform, language, value))

        async def owner_fetch_platform_list(self) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_platform_list from yj_platform_fetch_list()")
                    result = await cur.fetchone()
                    return result['o_platform_list']

        async def get_platform(self, platform_id: int) -> Dict[str, Any]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_platform from yj_platform_get(%s)", (platform_id,))
                    result = await cur.fetchone()
                    return result['o_platform']

        async def edit_platform(self,
                                platform_id: int,
                                name: str,
                                carousels_album_id: Optional[int] = None,
                                referrer_album_id: Optional[int] = None,
                                intro: Optional[str] = None,
                                language: Optional[str] = None,
                                order_pay_methods: Optional[List[Dict[str, Any]]] = None,
                                user_service_agreement_id: Optional[int] = None,
                                privacy_policy_agreement_id: Optional[int] = None,
                                sales_contract_and_hosting_service_agreement_id: Optional[int] = None,
                                about_us_agreement_id: Optional[int] = None,
                                customer_service_contact: Optional[Dict[str, Any]] = None):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_edit(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (platform_id, name, carousels_album_id, referrer_album_id, intro, language, json.dumps(order_pay_methods), user_service_agreement_id, privacy_policy_agreement_id, sales_contract_and_hosting_service_agreement_id, about_us_agreement_id, json.dumps(customer_service_contact)))

        async def fetch_agreement_list(self, platform_id: int) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_agreement_list from yj_fetch_agreement_list(%s)", (platform_id,))
                    result = await cur.fetchone()
                    return result['o_agreement_list']

        async def get_agreement(self, id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_agreement from yj_get_agreement(%s)", (id,))
                    result = await cur.fetchone()
                    return result['o_agreement'] if result else None

        async def create_agreement(self, platform_id: int, title: str, content: str) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_agreement_id from yj_agreement_create(%s, %s, %s)", (platform_id, title, content))
                    result = await cur.fetchone()
                    return result['o_agreement_id']

        async def edit_agreement(self, id: int, title: str, content: str):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_agreement_edit(%s, %s, %s)", (id, title, content))

        async def get_notice(self, id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_notice from yj_platform_get_notice(%s)", (id,))
                    result = await cur.fetchone()
                    return result['o_notice'] if result else None

        async def fetch_notice_list(self, platform_id: int) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_notice_list from yj_platform_fetch_notice_list(%s)", (platform_id,))
                    result = await cur.fetchone()
                    return result['o_notice_list']

        async def create_notice(self, platform_id: int, title: str, content: str,
                                display_popup: bool = False, read_confirm: bool = False) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_notice_id from yj_notice_create(%s, %s, %s, %s, %s)", (platform_id, title, content, display_popup, read_confirm))
                    result = await cur.fetchone()
                    return result['o_notice_id']

        async def edit_notice(self, id: int, title: str, content: str, display_popup: bool = False, read_confirm=False):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_notice_edit(%s, %s, %s, %s, %s)", (id, title, content, display_popup, read_confirm))

        async def publish_notice(self, id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_notice_publish(%s)", (id,))

        async def revoke_notice(self, id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_notice_revoke(%s)", (id,))

        async def create_album(self, platform_id: int, title: str) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_album_id from yj_album_create(%s, %s)", (platform_id, title))
                    result = await cur.fetchone()
                    return result['o_album_id']

        async def get_photo(self, id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_photo from yj_get_photo(%s)", (id, ))
                    result = await cur.fetchone()
                    return result['o_photo'] if result else None

        async def remove_photo(self, id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_remove_photo(%s)", (id, ))

        async def upload_photo(self, platform_id: int, mime_type: str, height: int, width: int, photo: str, album_id: Optional[int] = None) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_photo_id from yj_photo_upload(%s, %s, %s, %s, %s, %s)", (platform_id, mime_type, height, width, photo, album_id))
                    result = await cur.fetchone()
                    return result['o_photo_id']

        async def fetch_album_photos(self, id: int) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_album from yj_fetch_album_photos(%s)", (id, ))
                    result = await cur.fetchone()
                    return result['o_album']

        async def get_customer(self, id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_customer from yj_get_customer(%s)", (id, ))
                    result = await cur.fetchone()
                    return result['o_customer']

        async def rebind_customer_referrer(self, id: int, referrer_id: int, platform_id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_customer_rebind_referrer(%s, %s, %s)", (id, referrer_id, platform_id))

        async def fetch_customer_list(self, platform_id: int, filter_by: str, filter: str) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_customer_list from yj_fetch_customer_list(%s, %s, %s)", (platform_id, filter_by, filter))
                    result = await cur.fetchone()
                    return result['o_customer_list']

        async def create_customer(self,
                                  platform_id: int,
                                  mobile: str,
                                  nick_name: Optional[str] = None,
                                  internal_remarks_name: Optional[str] = None,
                                  description: Optional[str] = None,
                                  referrer_customer_id: Optional[int] = None) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_customer_id from yj_customer_create(%s, %s, %s, %s, %s, %s)", (platform_id, mobile, nick_name, internal_remarks_name, description, referrer_customer_id))
                    result = await cur.fetchone()
                    return result['o_customer_id']

        async def edit_customer(self, id: int, nick_name: Optional[str], internal_remarks_name: Optional[str], description: Optional[str]):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_customer_edit(%s, %s, %s, %s)", (id, nick_name, internal_remarks_name, description))

        async def fetch_referrer_list(self, platform_id: int) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_referrer_list from yj_fetch_referrer_list(%s)", (platform_id, ))
                    result = await cur.fetchone()
                    return result['o_referrer_list']

        async def get_referrer(self, Id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_referrer from yj_get_referrer(%s)", (Id, ))
                    result = await cur.fetchone()
                    return result['o_referrer']

        async def get_referrer_customer_list(self, Id: int) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_customer_list from yj_get_referrer_customer_list(%s)", (Id, ))
                    result = await cur.fetchone()
                    return result['o_customer_list']

        async def set_referrer_commission(self, Id: int, commission_rate: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_set_referrer_commission(%s, %s)", (Id, commission_rate))

        async def fetch_product_list(self, platform_id: int) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_product_list from yj_platform_fetch_product_list(%s)", (platform_id,))
                    result = await cur.fetchone()
                    return result['o_product_list']

        async def get_product(self, id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_product from yj_platform_get_product(%s)", (id,))
                    result = await cur.fetchone()
                    return result['o_product']

        async def create_product(self,
                                 platform_id: int,
                                 name: str,
                                 sale_method: str,
                                 sale_unit: int,
                                 min_units_for_sale: int,
                                 stock_qty: int,
                                 price: int,
                                 market_price: int,
                                 service_fee_percent: int,
                                 hosting_days: int,
                                 cover_photo_id: int,
                                 photos_album_id: int,
                                 sales_keywords: List[str],
                                 intro: Optional[str] = None,
                                 description: Optional[str] = None) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_product_id from yj_product_create(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (
                        platform_id, name, sale_method, sale_unit, min_units_for_sale, stock_qty, price, market_price, service_fee_percent,
                        hosting_days, cover_photo_id, photos_album_id, sales_keywords, intro, description))
                    result = await cur.fetchone()
                    return result['o_product_id']

        async def edit_product(self,
                               id: int,
                               name: str,
                               sale_unit: int,
                               min_units_for_sale: int,
                               stock_qty: int,
                               price: int,
                               market_price: int,
                               service_fee_percent: int,
                               hosting_days: int,
                               cover_photo_id: int,
                               photos_album_id: int,
                               sales_keywords: List[str],
                               intro: Optional[str] = None,
                               description: Optional[str] = None):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_edit_product(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (
                        id, name, sale_unit, min_units_for_sale, stock_qty, price, market_price, service_fee_percent,
                        hosting_days, cover_photo_id, photos_album_id, sales_keywords, intro, description))

        async def change_product_state(self, id: int, state: str):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_product_change_state(%s, %s)", (id, state))

        async def purchase_product(self, id: int, customer_id: int, qty: int, paid_amount: int, grant_qty: int, internal_comment: Optional[str] = None) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_product_purchase(%s, %s, %s, %s, %s, %s) as order_id", (
                        id, customer_id, qty, paid_amount, grant_qty, internal_comment))
                    result = await cur.fetchone()
                    return result['order_id']

        async def get_order(self, id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_order from yj_platform_get_order(%s)", (id, ))
                    result = await cur.fetchone()
                    return result['o_order']

        async def fetch_order_list(self, platform_id: int, filter_by: str, filter: Optional[str] = None) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_order_list from yj_platform_fetch_order_list(%s, %s, %s)", (platform_id, filter_by, filter))
                    result = await cur.fetchone()
                    return result['o_order_list']

        async def comment_order(self, id: int, comment: str):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_comment_order(%s, %s)", (id, comment))

        async def cancel_order(self, id: int, reason: str):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_order_cancel(%s, %s)", (id, reason))

        async def refuse_order_cancel(self, id: int, refuse_reason: Optional[str] = None):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_order_cancel_refuse(%s, %s)", (id, refuse_reason))

        async def confirm_order_cancel(self, id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_order_cancel_confirm(%s)", (id,))

        async def complete_order_payment(self, id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_order_payment_complete(%s)", (id,))

        async def complete_order_seal_cost_payment(self, id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_order_seal_cost_payment_complete(%s)", (id,))

        async def edit_order_seal_cost_required(self, id: int, pledge_amount: int, gas_amount: int):
            async with self.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("select yj_platform_edit_order_seal_cost_required(%s, %s, %s)", (id, pledge_amount, gas_amount))

        async def start_order_sealing(self, id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_order_sealing_start(%s)", (id,))

        async def start_order_mining(self, id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_order_mining_start(%s)", (id,))

        async def finish_order(self, id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_order_finish(%s)", (id,))

        async def create_order_fiat_payment(self,
                                            id: int,
                                            bank_name: str,
                                            bank_statement_no: str,
                                            amount: int,
                                            payment_screenshots: Optional[str] = None,
                                            comment: Optional[str] = None) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_payment_id from yj_order_fiat_payment_create(%s, %s, %s, %s, %s, %s)", (id, bank_name, bank_statement_no, amount, payment_screenshots, comment))
                    result = await cur.fetchone()
                    return result['o_payment_id']

        async def fetch_order_fiat_payment_list(self,
                                                platform_id: int,
                                                filter_by: str,
                                                filter: Optional[str] = None) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_payment_list from yj_order_fiat_payment_fetch_list(%s, %s, %s)", (platform_id, filter_by, filter))
                    result = await cur.fetchone()
                    return result['o_payment_list']

        async def create_order_crypto_payment(self,
                                              id: int,
                                              currency: str,
                                              amount: int,
                                              tx_or_message_id: str,
                                              comment: Optional[str]) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_payment_id from yj_order_crypto_payment_create(%s, %s, %s, %s, %s)", (id, currency, amount, tx_or_message_id, comment))
                    result = await cur.fetchone()
                    return result['o_payment_id']

        async def fetch_order_crypto_payment_list(self,
                                                  platform_id: int,
                                                  filter_by: str,
                                                  filter: Optional[str] = None) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_payment_list from yj_order_crypto_payment_fetch_list(%s, %s, %s)", (platform_id, filter_by, filter))
                    result = await cur.fetchone()
                    return result['o_payment_list']

        async def get_filecoin_order_seal_cost(self, order_id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_seal_cost from yj_get_filecoin_order_seal_cost(%s)", (order_id,))
                    result = await cur.fetchone()
                    return result['o_seal_cost']

        async def get_filecoin_seal_cost_payment_list(self, platform_id: int, filter_by: str, filter: Optional[str] = None) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_payment_list from yj_platform_fetch_filecoin_seal_cost_payment_list(%s, %s, %s)", (platform_id, filter_by, filter))
                    result = await cur.fetchone()
                    return result['o_payment_list']

        async def create_filecoin_seal_cost_payment(self, order_id: int, payment_type: str, message_id: str, to_address: str, amount: int, comment: Optional[str]) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_payment_id from yj_platform_filecoin_seal_cost_payment_create(%s, %s, %s, %s, %s, %s)", (order_id, payment_type, message_id, to_address, amount, comment))
                    result = await cur.fetchone()
                    return result['o_payment_id']

        async def fetch_filecoin_withdraw_list(self, platform_id: int, filter_by: str, filter: Optional[str] = None) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_withdraw_list from yj_platform_filecoin_withdraw_fetch_list(%s, %s, %s)", (platform_id, filter_by, filter))
                    result = await cur.fetchone()
                    return result['o_withdraw_list']

        async def get_filecoin_withdraw(self, id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_withdraw from yj_platform_filecoin_withdraw_get(%s)", (id,))
                    result = await cur.fetchone()
                    return result['o_withdraw']

        async def process_filecoin_withdraw_apply(self, id: int, comment: Optional[str] = None):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_filecoin_withdraw_process_apply(%s, %s)", (id, comment))

        async def complete_filecoin_withdraw_apply(self, id: int, message_id: str, comment: Optional[str] = None):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_filecoin_withdraw_complete_apply(%s, %s, %s)", (id, message_id, comment))

        async def refuse_filecoin_withdraw_apply(self, id: int, comment: Optional[str] = None):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_platform_filecoin_withdraw_apply_refuse(%s, %s)", (id, comment))

        async def get_filecoin_storage(self, order_id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_storage from yj_platform_filecoin_storage_get(%s)", (order_id,))
                    result = await cur.fetchone()
                    return result['o_storage']

        async def fetch_filecoin_storage_list(self, platform_id: int, filter_by: str, filter: Optional[str] = None):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_storage_list from yj_platform_filecoin_storage_fetch_list(%s, %s, %s)", (platform_id, filter_by, filter))
                    result = await cur.fetchone()
                    return result['o_storage_list']

        async def add_filecoin_sealed_storage(self, order_id: int, storage: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_filecoin_storage_add_sealed_storage(%s, %s)", (order_id, storage))

        async def create_filecoin_settlement(self, platform_id: int, mining_efficiency: int, comment: Optional[str] = None) -> str:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_settlement_no from yj_customer_filecoin_settlement_create(%s, %s, %s)", (platform_id, mining_efficiency, comment))
                    result = await cur.fetchone()
                    return result['o_settlement_no']

        async def create_filecoin_settlement_in_day(self, platform_id: int, settle_day_at: date, mining_efficiency: int, comment: Optional[str] = None) -> str:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_settlement_no from yj_customer_filecoin_settlement_day_create(%s, %s, %s, %s)", (platform_id, settle_day_at, mining_efficiency, comment))
                    result = await cur.fetchone()
                    return result['o_settlement_no']

        async def confirm_filecoin_settlement(self, settlement_no: str, mining_efficiency: int, comment: Optional[str] = None):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_customer_filecoin_settlement_confirm(%s, %s, %s)", (settlement_no, comment, mining_efficiency))

        async def fetch_filecoin_settlement_list(self, platform_id: int, filter_by: str, filter: Optional[str] = None) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_settlement_list from yj_filecoin_settlement_fetch_list(%s, %s, %s)", (platform_id, filter_by, filter))
                    result = await cur.fetchone()
                    return result['o_settlement_list']

        async def get_filecoin_settlement(self, platform_id: int, settlement_no: str) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_settlement from yj_filecoin_settlement_get_line(%s, %s)", (platform_id, settlement_no))
                    result = await cur.fetchone()
                    return result['o_settlement']

        async def fetch_filecoin_settlement_platform_list(self, platform_id: int, filter_by: str, filter: Optional[str] = None) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_settlement_list from yj_filecoin_settlement_platform_fetch_list(%s, %s, %s)", (platform_id, filter_by, filter))
                    result = await cur.fetchone()
                    return result['o_settlement_list']

        async def get_filecoin_settlement_platform(self, platform_id: int, settlement_no: str) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_settlement from yj_filecoin_settlement_platform_get_line(%s, %s)", (platform_id, settlement_no))
                    result = await cur.fetchone()
                    return result['o_settlement']

        async def get_filecoin_settlement_referrer(self, platform_id: int, settlement_no: str) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_settlement from yj_filecoin_settlement_referrer_get_line(%s, %s)", (platform_id, settlement_no))
                    result = await cur.fetchone()
                    return result['o_settlement']

        async def get_filecoin_settlement_referrer_list(self, platform_id: int, filter_by: str, filter: Optional[str] = None) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_settlement_list from yj_filecoin_settlement_referrere_fetch_list(%s, %s, %s)", (platform_id, filter_by, filter))
                    result = await cur.fetchone()
                    return result['o_settlement_list']

        async def get_filecoin_statitics(self, platform_id: int) -> Dict[str, Any]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_statitics from yj_platform_filecoin_statitics(%s)", (platform_id, ))
                    result = await cur.fetchone()
                    return result['o_statitics']

        async def bind_fil_withdraw_address(self, platform_id: int, address: str):
            async with self.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("select yj_platform_bind_filecoin_withdraw_address(%s, %s)", (platform_id, address))

        async def apply_platform_filecoin_withdraw(self, platform_id: int, amount: int) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_result from yj_platform_filecoin_platform_withdraw_apply(%s, %s)", (platform_id, amount))
                    result = await cur.fetchone()
                    return result['o_result']

        async def owner_process_platform_filecoin_withdraw_apply(self, withdraw_no: str, comment: Optional[str] = None):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_owner_filecoin_process_platform_withdraw_apply(%s, %s)", (withdraw_no, comment))

        async def owner_complete_platform_filecoin_withdraw_apply(self, withdraw_no: str, message_id: str):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_owner_filecoin_complete_platform_withdraw_apply(%s, %s)", (withdraw_no, message_id))

        async def owner_refuse_platform_filecoin_withdraw_apply(self, withdraw_no: str, comment: Optional[str] = None):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_owner_filecoin_refuse_platform_withdraw_apply(%s, %s)", (withdraw_no, comment))

        async def owner_fetch_platform_filecoin_withdraw_apply_list(self, platform_id: int, state: str) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_withdraw_apply_list from yj_owner_filecoin_fetch_platform_withdraw_apply_list(%s, %s)", (platform_id, state))
                    result = await cur.fetchone()
                    return result['o_withdraw_apply_list']

        async def owner_fetch_platform_filecoin_withdraw_list(self, platform_id: int) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_withdraw_list from yj_owner_filecoin_fetch_platform_withdraw_list(%s)", (platform_id,))
                    result = await cur.fetchone()
                    return result['o_withdraw_list']

        async def fetch_platform_filecoin_withdraw_apply_list(self, platform_id: int, state: str) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_withdraw_apply_list from yj_platform_filecoin_fetch_platform_withdraw_apply_list(%s, %s)", (platform_id, state))
                    result = await cur.fetchone()
                    return result['o_withdraw_apply_list']

        async def fetch_platform_filecoin_withdraw_list(self, platform_id: int) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_withdraw_list from yj_platform_filecoin_fetch_platform_withdraw_list(%s)", (platform_id,))
                    result = await cur.fetchone()
                    return result['o_withdraw_list']

        async def create_flash(self, platform_id: int, title: str, content: str, display_popup: bool = False, read_confirm: bool = False) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_flash_id from yj_flash_create(%s, %s, %s, %s, %s)", (platform_id, title, content, display_popup, read_confirm))
                    result = await cur.fetchone()
                    return result['o_flash_id']

        async def fetch_flash_list(self, platform_id: int) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_flash_list from yj_platform_fetch_flash_list(%s)", (platform_id,))
                    result = await cur.fetchone()
                    return result['o_flash_list']

        async def get_flash(self, id: int) -> Optional[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_flash from yj_platform_get_flash(%s)", (id,))
                    result = await cur.fetchone()
                    return result['o_flash'] if result else None

        async def edit_flash(self, id: int, title: str, content: str, display_popup: bool = False, read_confirm=False):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_flash_edit(%s, %s, %s, %s, %s)", (id, title, content, display_popup, read_confirm))

        async def publish_flash(self, id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_flash_publish(%s)", (id,))

        async def revoke_flash(self, id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_flash_revoke(%s)", (id,))

        async def fetch_owner_get_filecoin_statitics(self) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_statitics from yj_owner_platform_filecoin_statitics()")
                    result = await cur.fetchone()
                    return result['o_statitics']

        async def fetch_owner_get_filecoin_profites_list(self, settle_day_at: date) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_profites_list from yj_owner_platform_filecoin_profites_list(%s)", (settle_day_at,))
                    result = await cur.fetchone()
                    return result['o_profites_list']

        async def edit_seal_cost(self, platform_id: int, id: int, amount: int) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_payment_id from yj_edit_seal_cost(%s, %s, %s)", (platform_id, id, amount))
                    result = await cur.fetchone()
                    return result['o_payment_id']

        async def fetch_owner_get_platform_customer_filecoin_withdraw_list(self, platform_id: int) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_withdraw_list from yj_fetch_owner_get_platform_customer_filecoin_withdraw_list(%s)", (platform_id,))
                    result = await cur.fetchone()
                    return result['o_withdraw_list']

        async def discarded_filecoin_settlement(self, platform_id: int, settlement_no: str):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_discarded_filecoin_settlement(%s,%s)", (platform_id, settlement_no))

        async def fetch_owner_get_customer_independent_node_list(self, mobile: str, node_no: str, state: str) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_customer_node_list from yj_fetch_owner_get_customer_independent_node_list(%s, %s, %s)", (mobile, node_no, state))
                    result = await cur.fetchone()
                    return result['o_customer_node_list']

        async def fetch_owner_get_customer_list(self, filter_by: str, filter: str) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_owner_customer_list from yj_fetch_owner_get_customer_list(%s, %s)", (filter_by, filter))
                    result = await cur.fetchone()
                    return result['o_owner_customer_list']

        async def add_owner_customer_independent_node(self, customer_id: int, node_no: str, node_comment: str):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_add_owner_customer_independent_node(%s, %s, %s)", (customer_id, node_no, node_comment))

        async def edit_owner_customer_independent_node(self, id: int, node_no: str, node_comment: str, withdrawn_address: str):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_owner_customer_independent_node_edit(%s, %s, %s, %s)", (id, node_no, node_comment, withdrawn_address))

        async def finish_owner_customer_independent_node(self, id: int):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_finish_owner_customer_independent_node(%s)", (id,))

        async def fetch_owner_customer_independent_node_withdraw_list(self, filter_by: str, filter: str) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_customer_node_withdraw_list from yj_fetch_owner_customer_independent_node_withdraw_list(%s, %s)", (filter_by, filter))
                    result = await cur.fetchone()
                    return result['o_customer_node_withdraw_list']

        async def process_owner_customer_independent_node_withdraw_apply(self, withdraw_no: str, comment: Optional[str] = None):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_process_owner_customer_independent_node_withdraw_apply(%s, %s)", (withdraw_no, comment))

        async def complete_owner_customer_independent_node_withdraw_apply(self, withdraw_no: str, message_id: str):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_complete_owner_customer_independent_node_withdraw_apply(%s, %s)", (withdraw_no, message_id))

        async def refuse_owner_customer_independent_node_withdraw_apply(self, withdraw_no: str, comment: Optional[str] = None):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_refuse_owner_customer_independent_node_withdraw_apply(%s, %s)", (withdraw_no, comment))

        async def fetch_owner_customer_expenses_list(self, filter_by: str, filter: str) -> List[Dict[str, Any]]:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select o_owner_filecoin_customer_expenses_list from yj_owner_filecoin_customer_expenses_list(%s, %s)", (filter_by, filter))
                    result = await cur.fetchone()
                    return result['o_owner_filecoin_customer_expenses_list']

        async def add_owner_customer_expenses(self, customer_id: int, expenses_type: str, expenses_amount: int, reason: str, comment: str):
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_owner_filecoin_customer_expenses_add(%s, %s, %s, %s, %s)", (customer_id, expenses_type, expenses_amount, reason, comment))

        async def fetch_owner_customer_avaiable_amount(self, customer_id: int) -> int:
            async with self.db.acquire() as conn:
                async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    await cur.execute("select yj_get_customer_avaiable_amount(%s)", (customer_id,))
                    result = await cur.fetchone()
                    return int(result[0])

        async def fetch_owner_get_settlement_newest_list(self) -> List[Dict[str, Any]]:
          async with self.db.acquire() as conn:
              async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                  await cur.execute("select o_settlement_list from yj_filecoin_owner_settlement_newest_fetch_list()")
                  result = await cur.fetchone()
                  return result['o_settlement_list'][0]

        async def stop_customer_orders(self,platform_id: int,customer_id: int) -> int:
          async with self.db.acquire() as conn:
              async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                  await cur.execute("select yj_filecoin_stop_customer_orders(%s,%s)",(platform_id,customer_id))

        async def customer_clearing_fee(self,platform_id: int,customer_id: int,amount: int) -> int:
          async with self.db.acquire() as conn:
              async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                  await cur.execute("select yj_customer_clearing_fee(%s,%s,%s)",(platform_id,customer_id,amount))

        async def order_stop(self,platform_id: int,order_id: int,few_days: int) -> int:
          async with self.db.acquire() as conn:
              async with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                  await cur.execute("select yj_stop_order(%s,%s,%s)",(platform_id,order_id,few_days))


async def _on_startup(app: web.Application):
    db = await Database.create(app)
    app['db'] = db
    for sub in app._subapps:
        sub['db'] = db


async def _on_cleanup(app: web.Application):
    await app['db'].close()


def setup(app: web.Application):
    app.on_startup.append(_on_startup)
    app.on_cleanup.append(_on_cleanup)
