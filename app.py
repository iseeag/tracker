import asyncio
from traceback import format_exc

import streamlit as st
from loguru import logger

from database import CredentialManager, UserManager, init_db
from simple_asset_tracker import SimpleAssetTracker

# Configure logger
logger.add("app.log", rotation="500 MB", retention="10 days")

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None


def login_user(username: str, password: str) -> bool:
    logger.info(f"Login attempt for user: {username}")
    user = UserManager.verify_user(username, password)
    if user:
        logger.info(f"Login successful for user: {username}")
        st.session_state.user = user
        return True
    logger.warning(f"Failed login attempt for user: {username}")
    return False


def logout_user():
    st.session_state.user = None


def register_user(username: str, password: str) -> bool:
    logger.info(f"Registration attempt for username: {username}")
    success = UserManager.create_user(username, password)
    if success:
        logger.info(f"Registration successful for username: {username}")
    else:
        logger.warning(f"Registration failed for username: {username}")
    return success


def render_login_section():
    st.subheader("登录 / 注册")

    tab1, tab2 = st.tabs(["登录", "注册"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            submitted = st.form_submit_button("登录")

            if submitted:
                if login_user(username, password):
                    st.success("登录成功！")
                    st.rerun()
                else:
                    st.error("用户名或密码错误")

    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("用户名")
            new_password = st.text_input("密码", type="password")
            confirm_password = st.text_input("确认密码", type="password")
            submitted = st.form_submit_button("注册")

            if submitted:
                if new_password != confirm_password:
                    st.error("两次输入的密码不一致")
                elif register_user(new_username, new_password):
                    st.success("注册成功！请登录。")
                else:
                    st.error("注册失败。用户名可能已被使用。")


def render_credential_section():
    st.subheader("凭证管理")

    credentials = CredentialManager.get_credentials(st.session_state.user['id'])

    with st.expander("添加新凭证"):
        with st.form("add_credential"):
            label = st.text_input("标签")
            api_key = st.text_input("API KEY")
            api_secret = st.text_input("API SECRET", type="password")
            initial_value = st.number_input("初始投资额 (USD)", min_value=0.0)
            submitted = st.form_submit_button("添加凭证")

            if submitted:
                if CredentialManager.add_credential(
                        st.session_state.user['id'], api_key, api_secret,
                        initial_value, label
                ):
                    st.success("凭证添加成功！")
                    st.rerun()
                else:
                    st.error("添加凭证失败")

    for cred in credentials:
        with st.expander(f"凭证: {cred['label']}"):
            with st.form(f"edit_credential_{cred['id']}"):
                new_label = st.text_input("标签", value=cred['label'])
                new_api_key = st.text_input("API密钥", value=cred['api_key'])
                new_api_secret = st.text_input("API密钥", value=cred['api_secret'], type="password")
                new_initial_value = st.number_input(
                    "初始投资额 (USD)",
                    value=float(cred['initial_value_usd']),
                    min_value=0.0
                )
                col1, col2 = st.columns(2)
                with col1:
                    update = st.form_submit_button("更新凭证")
                with col2:
                    delete = st.form_submit_button("删除凭证", type="primary")

                if update:
                    if CredentialManager.update_credential(
                            cred['id'], st.session_state.user['id'],
                            new_api_key, new_api_secret,
                            new_initial_value, new_label
                    ):
                        st.success("凭证更新成功！")
                        st.rerun()
                    else:
                        st.error("更新凭证失败")

                if delete:
                    if CredentialManager.delete_credential(cred['id'], st.session_state.user['id']):
                        st.success("凭证删除成功！")
                        st.rerun()
                    else:
                        st.error("删除凭证失败")


async def fetch_asset_data(credentials):
    logger.info("Starting to fetch asset data")
    all_data = []
    for cred in credentials:
        logger.debug(f"Fetching data for credential: {cred['label']}")
        tracker = SimpleAssetTracker(cred['api_key'], cred['api_secret'])
        try:
            data = await tracker.get_all_breakdowns()

            initial_value = float(cred['initial_value_usd'])
            pnl = data['total_value'] - initial_value
            pnl_percentage = (pnl / initial_value) * 100 if initial_value > 0 else 0

            all_data.append({
                'label': cred['label'],
                'total_value': data['total_value'],
                'spot': data['spot_breakdown'],
                'futures': data['futures_breakdown'],
                'margin': data['margin_breakdown'],
                'initial_value': initial_value,
                'pnl': pnl,
                'pnl_percentage': pnl_percentage
            })
        except Exception as e:
            logger.error(f"Error fetching data for {cred['label']}: {str(e)} {format_exc()}")
            st.error(f"Error fetching data for {cred['label']}: {str(e)}")
    logger.info("Completed fetching asset data")
    return all_data


def render_dashboard():
    st.subheader("资产仪表盘")

    credentials = CredentialManager.get_credentials(st.session_state.user['id'])
    if not credentials:
        st.info("未找到凭证。请在凭证管理部分添加凭证。")
        return

    # Add refresh button in the header
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.write("### 总览")
    with col2:
        if st.button("🔄 刷新"):
            st.cache_data.clear()
            st.rerun()

    @st.cache_data(ttl=300)  # Cache data for 5 minutes
    def get_cached_data(credentials_str):
        return asyncio.run(fetch_asset_data(credentials))

    # Use credentials as cache key
    credentials_str = str([(c['id'], c['label']) for c in credentials])
    data = get_cached_data(credentials_str)

    # Summary section
    total_value = sum(d['total_value'] for d in data)
    total_initial = sum(d['initial_value'] for d in data)
    total_pnl = sum(d['pnl'] for d in data)
    total_pnl_percentage = (total_pnl / total_initial) * 100 if total_initial > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总资产", f"${total_value:,.2f}")
    col2.metric("初始投资", f"${total_initial:,.2f}")
    col3.metric("总盈亏", f"${total_pnl:,.2f}")
    col4.metric("总盈亏率", f"{total_pnl_percentage:.2f}%")

    # Individual credential sections
    st.write("### 账户详情")
    for d in data:
        with st.expander(f"{d['label']}"):
            # Main metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("总资产", f"${d['total_value']:,.2f}")
                st.metric("初始投资", f"${d['initial_value']:,.2f}")
            with col2:
                st.metric("总盈亏", f"${d['pnl']:,.2f}")
                st.metric("盈亏率", f"{d['pnl_percentage']:.2f}%")

            # Spot breakdown
            st.write("#### 现货账户")
            st.metric("现货总值", f"${d['spot']['total_value']:,.2f}")

            # Margin breakdown
            st.write("#### 杠杆账户")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总资产", f"${d['margin']['total_asset_usd']:,.2f}")
            with col2:
                st.metric("总负债", f"${d['margin']['total_liability_usd']:,.2f}")
            with col3:
                st.metric("净资产", f"${d['margin']['total_net_asset_usd']:,.2f}")

            # Futures breakdown
            st.write("#### 合约账户")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("钱包余额", f"${d['futures']['wallet_balance']:,.2f}")
                st.metric("保证金余额", f"${d['futures']['margin_balance']:,.2f}")
                st.metric("可用余额", f"${d['futures']['available_balance']:,.2f}")
            with col2:
                st.metric("未实现盈亏", f"${d['futures']['unrealized_pnl']:,.2f}")
                st.metric("全仓钱包余额", f"${d['futures']['cross_wallet_balance']:,.2f}")
                st.metric("全仓未实现盈亏", f"${d['futures']['cross_upnl']:,.2f}")

            # USDT-M and Coin-M Futures breakdown
            col1, col2 = st.columns(2)
            with col1:
                st.write("##### U本位合约")
                st.metric("总余额", f"${d['futures']['futures_breakdown']['total_balance']:,.2f}")
                st.metric("总未实现盈亏", f"${d['futures']['futures_breakdown']['total_upnl']:,.2f}")
            with col2:
                st.write("##### 币本位合约")
                st.metric("总余额", f"${d['futures']['coin_futures_breakdown']['total_balance']:,.2f}")
                st.metric("总未实现盈亏", f"${d['futures']['coin_futures_breakdown']['total_upnl']:,.2f}")


def main():
    st.set_page_config(
        page_title="币安资产追踪器",
        page_icon="",
        layout="wide"
    )

    st.title("")

    # Initialize database
    init_db()

    # Render logout button if user is logged in
    if st.session_state.user:
        st.sidebar.button("登出", on_click=logout_user)
        st.sidebar.write(f"登录用户: {st.session_state.user['username']}")

    if not st.session_state.user:
        render_login_section()
    else:
        tab1, tab2 = st.tabs(["仪表盘", "凭证管理"])

        with tab1:
            render_dashboard()

        with tab2:
            render_credential_section()


if __name__ == "__main__":
    main()
