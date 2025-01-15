from datetime import datetime
from typing import Dict, Tuple

import gradio as gr
import pandas as pd

from gr_backend import admin_login, create_account, create_strategy
from gr_backend import create_user as create_user_backend
from gr_backend import delete_account as delete_account_backend
from gr_backend import delete_strategy as delete_strategy_backend
from gr_backend import delete_user as delete_user_backend
from gr_backend import get_account as get_account_backend
from gr_backend import get_db
from gr_backend import get_strategy as get_strategy_backend
from gr_backend import get_tables as get_tables_backend
from gr_backend import get_user as get_user_backend
from gr_backend import get_user_linked_accounts
from gr_backend import list_accounts as list_accounts_backend
from gr_backend import list_user_linked_accounts
from gr_backend import list_users as list_users_backend
from gr_backend import logout as user_logout_backend
from gr_backend import update_account
from gr_backend import update_strategy as update_strategy_backend
from gr_backend import update_user as update_user_backend
from gr_backend import user_login as user_login_backend
from gr_backend import validate_exchange_credentials


def null_check(*args):
    if not all([*args]):
        raise gr.Error("所有字段都是必填的!")


# ######### backends ###########
def master_login(master_token) -> Tuple[str, str]:
    token = admin_login(master_token)
    if not token:
        return "", "登录失败"
    return token, "登录成功!"


def user_login(token: str) -> Tuple[str, str]:
    token = user_login_backend(token, next(get_db()))
    if not token:
        return "", "登录失败"
    return token, "登录成功! 资产余额将自动加载！"


def logout(token) -> Tuple[str, str]:
    if user_logout_backend(token):
        return "", "登出成功!"
    return "", "登出失败"


def add_account(token, account_name, start_date: float):
    null_check(account_name, start_date)
    db = next(get_db())
    start_date = (datetime.fromtimestamp(start_date)).strftime("%Y-%m-%d")
    try:
        create_account(token, account_name, start_date, db)
        return "账户添加成功!"
    except Exception as e:
        return f"添加账户失败: {str(e)}"


def modify_account(token, account_name, start_date):
    null_check(account_name, start_date)
    db = next(get_db())
    start_date = (datetime.fromtimestamp(start_date)).strftime("%Y-%m-%d")
    if update_account(token, account_name, start_date, db):
        return "账户更新成功!"
    return "账户更新失败."


def delete_account(token, account_name):
    null_check(account_name)
    db = next(get_db())
    try:
        if delete_account_backend(token, account_name, db):
            return "账户删除成功!"
        return "账户删除失败."
    except Exception as e:
        return f"删除账户失败: {str(e)}"


def update_selectable_accounts(token) -> gr.Dropdown:
    if not token:
        return gr.Dropdown(choices=[])
    db = next(get_db())
    accounts = list_accounts_backend(token, db)
    account_names = [account.account_name for account in accounts]
    return gr.Dropdown(choices=account_names)


def add_strategy(token, account_name, strategy_name, api_key, secret_key, passphrase, exchange_type, preset_balance):
    null_check(account_name, strategy_name, api_key, secret_key, exchange_type, preset_balance)
    try:
        preset_balance = float(preset_balance)
    except ValueError:
        raise gr.Error("预设余额必须是数字!")

    db = next(get_db())
    try:
        create_strategy(token, account_name, strategy_name, api_key, secret_key, passphrase, exchange_type,
                        preset_balance, db)
        return "策略添加成功!"
    except Exception as e:
        return f"添加策略失败: {str(e)}"


def get_strategy(token, account_name, strategy_name) -> Tuple[str, str, str, gr.Dropdown, str]:
    null_check(account_name, strategy_name)
    db = next(get_db())
    strategy = get_strategy_backend(token, account_name, strategy_name, db)
    if not strategy:
        return "", "", "", gr.Dropdown(value=''), ""
    return (strategy.api_key, strategy.secret_key, strategy.passphrase,
            gr.Dropdown(value=strategy.exchange_type), strategy.preset_balance)


def update_strategy(token, account_name, strategy_name, api_key, secret_key, passphrase, exchange_type, preset_balance):
    null_check(account_name, strategy_name, api_key, secret_key, exchange_type, preset_balance)
    try:
        preset_balance = float(preset_balance)
    except ValueError:
        raise gr.Error("预设余额必须是数字!")

    db = next(get_db())
    if update_strategy_backend(token, account_name, strategy_name, api_key, secret_key, passphrase, exchange_type,
                               preset_balance, db):
        return "策略更新成功!"
    return "策略更新失败."


def delete_strategy(token, account_name, strategy_name):
    null_check(account_name, strategy_name)
    db = next(get_db())
    if delete_strategy_backend(token, account_name, strategy_name, db):
        return "策略删除成功!"
    return "策略删除失败."


def validate_strategy(api_key, secret_key, passphrase, exchange_type):
    null_check(api_key, secret_key, passphrase, exchange_type)
    if validate_exchange_credentials(exchange_type, api_key, secret_key, passphrase):
        return "帐秘有效!"
    return "帐秘无效!"


def add_user(token, name, login_token, linked_accounts):
    null_check(name, login_token)
    db = next(get_db())
    if create_user_backend(token, name, login_token, linked_accounts, db):
        return "用户添加成功!"
    return f"添加用户失败!"


def update_selectable_users(token) -> gr.Dropdown:
    db = next(get_db())
    users = list_users_backend(token, db)
    return gr.Dropdown(choices=[user.name for user in users])


def remove_user(token, name):
    null_check(name)
    db = next(get_db())
    if delete_user_backend(token, name, db):
        return "用户删除成功!"
    return "用户删除失败."


def update_user(token, name, login_token, linked_accounts):
    null_check(name, login_token)
    db = next(get_db())
    if update_user_backend(token, name, login_token, linked_accounts, db):
        return "用户更新成功!"
    return "用户更新失败."


def get_tables(token, date_ranges: Dict[str, Tuple[str, str]] = None):
    null_check(token)
    db = next(get_db())

    return get_tables_backend(token, date_ranges, db)


# ######### ui react ###########
def toggle_panels_x3(token):
    visible = True if token else True  # todo: fix this
    return [gr.Group(visible=visible) for _ in range(3)]


def clear_account_fields():
    return gr.Dropdown(value=''), gr.Textbox(value=''), gr.DateTime(value=None)


def fill_account_fields(token, account_name):
    db = next(get_db())
    account = get_account_backend(token, account_name, db)
    return gr.Textbox(value=account.account_name), gr.DateTime(value=account.start_date.strftime("%Y-%m-%d"))


def clear_user_fields():
    return gr.Dropdown(value=''), gr.Textbox(value=''), gr.Textbox(value='')


def fill_user_fields(token, user_name):
    db = next(get_db())
    user = get_user_backend(token, user_name, db)
    linked_accounts = get_user_linked_accounts(user.name, db)
    linked_accounts = [str(a.account_name) for a in linked_accounts]
    return gr.Textbox(value=user.name), gr.Textbox(value=user.login_token), gr.CheckboxGroup(value=linked_accounts)


def fill_linked_accounts(token, user_name):
    db = next(get_db())
    accounts = list_accounts_backend(token, db)
    account_names = [account.account_name for account in accounts]
    linked_accounts = []
    if user_name:
        user = get_user_backend(token, user_name, db)
        if user:
            linked_accounts = get_user_linked_accounts(user.name, db)
    linked_accounts = [str(a.account_name) for a in linked_accounts]
    return gr.CheckboxGroup(choices=account_names, value=linked_accounts)


def update_tables_via_date_range_cfg(cfg):
    if cfg:
        cfg['counter'] += 1
        return cfg, f"实时余额更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    return cfg, "登录以查看余额!"


# Initialize Gradio interface
def admin_interface():
    session_token = gr.State("")  # Initialize empty session token

    with gr.Blocks() as admin_ui:
        with gr.Row():
            gr.Markdown("# 账户管理系统")
            action_status = gr.Textbox(label="状态信息", value="请先登录!", text_align="right")
        gr.Markdown("## 登录")
        with gr.Group():
            with gr.Row():
                master_token_input = gr.Textbox(label="管理员令牌", type="password", scale=3,
                                                value='20add5567250ccff972607fc1e516047')
                with gr.Column():
                    login_button = gr.Button("登录")
                    logout_button = gr.Button("登出")

        gr.Markdown("## 账户管理")
        with gr.Group(visible=False) as account_panel:
            with gr.Row():
                selected_account = gr.Dropdown(label="选择账户", choices=[], interactive=True)
                account_name_input = gr.Textbox(label="账户名称")
                start_date_input = gr.DateTime(label="开始日期", include_time=False)
                with gr.Column():
                    with gr.Row():
                        add_account_button = gr.Button("添加")
                        delete_account_button = gr.Button("删除")
                    with gr.Row():
                        update_account_button = gr.Button("更新")

        gr.Markdown("### 策略管理")
        with gr.Group(visible=False) as strategy_panel:
            with gr.Row():
                with gr.Column(scale=3):
                    with gr.Row():
                        selected_strategy = gr.Dropdown(
                            value='', label="选择策略", choices=['AI', 'DCA', 'CRYPTO', 'MARTINGALE'],
                            interactive=True)
                        preset_balance_input = gr.Textbox(label="预设余额")
                        exchange_type_input = gr.Dropdown(label="交易所类型", choices=["bitget", "binance"],
                                                          interactive=True, allow_custom_value=False)
                    with gr.Row():
                        api_key_input = gr.Textbox(label="API密钥")
                        secret_key_input = gr.Textbox(label="密钥", max_lines=1)
                        passphrase_input = gr.Textbox(label="密码短语", type="password")
                with gr.Column():
                    add_strategy_button = gr.Button("添加策略")
                    update_strategy_button = gr.Button("更新策略")
                    delete_strategy_button = gr.Button("删除策略")
                    validate_strategy_button = gr.Button("验证策略")

        gr.Markdown("## 用户管理")
        with gr.Group(visible=False) as user_panel:
            with gr.Row():
                selected_user = gr.Dropdown(label="选择用户", choices=[])
                user_name_input = gr.Textbox(label="用户名")
                login_token_input = gr.Textbox(label="登录令牌")
                with gr.Column():
                    with gr.Row():
                        add_user_button = gr.Button("添加用户")
                        delete_user_button = gr.Button("删除用户")
                    with gr.Row():
                        update_user_button = gr.Button("更新用户")

            linked_accounts = gr.CheckboxGroup(label="选择关联账户", choices=[], interactive=True)

        # ---- login ----
        login_action = login_button.click(
            fn=master_login, inputs=[master_token_input], outputs=[session_token, action_status])
        logout_button.click(fn=logout, inputs=[session_token], outputs=[session_token, action_status])
        session_token.change(
            fn=toggle_panels_x3, inputs=[session_token], outputs=[account_panel, strategy_panel, user_panel])
        # ---- account ----
        add_acc_action = add_account_button.click(
            fn=add_account, inputs=[session_token, account_name_input, start_date_input], outputs=[action_status])
        delete_acc_action = delete_account_button.click(
            fn=delete_account, inputs=[session_token, selected_account], outputs=[action_status])
        update_account_button.click(
            fn=modify_account, inputs=[session_token, account_name_input, start_date_input], outputs=[action_status])
        for a in [login_action, add_acc_action, delete_acc_action]:
            a.then(update_selectable_accounts, inputs=[session_token], outputs=[selected_account])
        for a in [add_acc_action, delete_acc_action]:
            a.then(clear_account_fields, outputs=[selected_account, account_name_input, start_date_input])
        selected_account.select(
            fill_account_fields, inputs=[session_token, selected_account],
            outputs=[account_name_input, start_date_input])
        # ---- strategy ----
        add_strategy_button.click(
            fn=add_strategy, inputs=[session_token, selected_account, selected_strategy, api_key_input,
                                     secret_key_input, passphrase_input, exchange_type_input, preset_balance_input],
            outputs=[action_status])
        update_strategy_button.click(update_strategy, inputs=[
            session_token, selected_account, selected_strategy, api_key_input, secret_key_input, passphrase_input,
            exchange_type_input, preset_balance_input], outputs=[action_status])
        delete_strategy_button.click(
            delete_strategy, inputs=[session_token, selected_account, selected_strategy], outputs=[action_status])
        validate_strategy_button.click(
            validate_strategy, inputs=[api_key_input, secret_key_input, passphrase_input, exchange_type_input],
            outputs=[action_status])
        selected_strategy.select(get_strategy, inputs=[session_token, selected_account, selected_strategy], outputs=[
            api_key_input, secret_key_input, passphrase_input, exchange_type_input, preset_balance_input])

        # ---- user ----
        add_user_action = add_user_button.click(
            add_user, inputs=[session_token, user_name_input, login_token_input, linked_accounts],
            outputs=[action_status])
        delete_user_action = delete_user_button.click(
            remove_user, inputs=[session_token, selected_user], outputs=[action_status])
        update_user_button.click(
            update_user, inputs=[session_token, user_name_input, login_token_input, linked_accounts],
            outputs=[action_status])
        for a in [login_action, add_user_action, delete_user_action]:
            a.then(update_selectable_users, inputs=[session_token], outputs=[selected_user])
        for a in [add_user_action, delete_user_action]:
            a.then(clear_user_fields, outputs=[selected_user, user_name_input, login_token_input])
        for a in [login_action, add_acc_action, delete_acc_action, add_user_action, delete_user_action]:
            a.then(fill_linked_accounts, inputs=[session_token, selected_user], outputs=[linked_accounts])
        selected_user.select(
            fill_user_fields, inputs=[session_token, selected_user],
            outputs=[user_name_input, login_token_input, linked_accounts])
    return admin_ui


def set_date_ranges(token, start_date: str = None, end_date: str = None, account_name: str = None):
    db = next(get_db())
    accounts = list_user_linked_accounts(token, db)
    default_ranges = {a.account_name: ('2025-01-01', '2025-02-01') for a in accounts}
    if start_date and end_date and account_name:
        default_ranges[account_name] = (start_date, end_date)
    return default_ranges


def set_date_range_config(token, start_date: str = None, end_date: str = None, account_name: str = None):
    return {'counter': 0, 'date_ranges': set_date_ranges(token, start_date, end_date, account_name)}


def user_interface():
    session_token = gr.State("")  # Initialize empty session token
    date_range_cfg = gr.State({})
    with gr.Blocks() as user_ui:
        with gr.Row():
            gr.Markdown("# 用户面板")
            action_status = gr.Textbox(label="状态信息", value="请先登录!", text_align="right")
        gr.Markdown("## 登录")
        with gr.Group():
            with gr.Row():
                login_token_input = gr.Textbox(label="登录令牌", type="password", scale=3, value='abc')
                with gr.Column():
                    login_button = gr.Button("登录")
                    logout_button = gr.Button("登出")

        with gr.Row():
            with gr.Column(scale=3):
                gr.Markdown(lambda: f"## 账户余额汇总 ", every=60)
            with gr.Column():
                latest_time_txt = gr.Textbox(lambda: f"最近更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                                             container=False, every=60, show_label=False, interactive=False)

        @gr.render([date_range_cfg, session_token])
        def render_tables(date_range_config, token):
            if token and date_range_config:
                balance_tables = get_tables(token, date_range_config['date_ranges'])
            else:
                balance_tables = {"summarized": pd.DataFrame(),
                                  "linked_accounts": [{
                                      'name': 'N/A',
                                      'start_date': '2025-01-01',
                                      "data": pd.DataFrame(),
                                      "history": {'start_date': '2025-01-01',
                                                  'end_date': '2026-01-01',
                                                  'data': pd.DataFrame()},
                                  }]}
            with gr.Row():
                gr.DataFrame(label="总余额", value=balance_tables["summarized"], show_label=False)
            gr.Markdown("## 账户详情")
            with gr.Group():
                for i, account in enumerate(balance_tables["linked_accounts"]):
                    account_name = account['name']
                    account_df = account['data']
                    account_start_date = account['start_date']
                    history_df = account['history']['data']
                    start_date, end_date = account['history']['start_date'], account['history']['end_date']
                    with gr.Accordion(label=f"< {account_name} > 自 {account_start_date} ", open=False):
                        gr.DataFrame(value=account_df, show_label=False)
                        gr.Markdown("### 账户余额历史")
                        with gr.Row():
                            start_date = gr.DateTime(
                                value=start_date, label="开始日期", include_time=False, interactive=True)
                            end_date = gr.DateTime(
                                value=end_date, label="结束日期", include_time=False, interactive=True)
                            with gr.Column():
                                gr.Textbox('', interactive=False, show_label=False, container=False)
                                reload_button = gr.Button("重新加载")
                        gr.DataFrame(scale=4, value=history_df)

                    def _set_date_range_config(s, sd, ed):
                        sd = (datetime.fromtimestamp(sd)).strftime("%Y-%m-%d")
                        ed = (datetime.fromtimestamp(ed)).strftime("%Y-%m-%d")
                        return set_date_range_config(s, sd, ed, account_name)

                    reload_button.click(
                        _set_date_range_config, inputs=[session_token, start_date, end_date], outputs=[date_range_cfg])

    login_action = login_button.click(fn=user_login, inputs=[login_token_input], outputs=[session_token, action_status])
    login_action.then(fn=set_date_range_config, inputs=[session_token], outputs=[date_range_cfg])
    logout_action = logout_button.click(fn=logout, inputs=[session_token], outputs=[session_token, action_status])
    logout_action.then(fn=lambda: {}, outputs=[date_range_cfg])
    latest_time_txt.change(update_tables_via_date_range_cfg, inputs=[date_range_cfg],
                           outputs=[date_range_cfg, action_status])

    return user_ui


if __name__ == "__main__":
    with gr.Blocks() as app:
        gr.Markdown("# 资产跟踪器")
        with gr.Tab("用户"):
            user_interface()
        with gr.Tab("管理员"):
            admin_interface()

    app.launch(inbrowser=True)
