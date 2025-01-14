from datetime import datetime
from typing import Dict, List, Tuple

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
        raise gr.Error("All fields are required!")


# ######### backends ###########
def master_login(master_token) -> Tuple[str, str]:
    token = admin_login(master_token)
    if not token:
        return "", "Login failed"
    return token, "Login successful!"


def user_login(token: str) -> Tuple[str, str]:
    token = user_login_backend(token, next(get_db()))
    if not token:
        return "", "Login failed"
    return token, "Login successful!"


def logout(token) -> Tuple[str, str]:
    if user_logout_backend(token):
        return "", "Logout successful!"
    return "", "Logout failed"


def add_account(token, account_name, start_date: float):
    null_check(account_name, start_date)
    db = next(get_db())
    start_date = (datetime.fromtimestamp(start_date)).strftime("%Y-%m-%d")
    try:
        create_account(token, account_name, start_date, db)
        return "Account added successfully!"
    except Exception as e:
        return f"Failed to add account: {str(e)}"


def modify_account(token, account_name, start_date):
    null_check(account_name, start_date)
    db = next(get_db())
    start_date = (datetime.fromtimestamp(start_date)).strftime("%Y-%m-%d")
    if update_account(token, account_name, start_date, db):
        return "Account updated successfully!"
    return "Account update failed."


def delete_account(token, account_name):
    null_check(account_name)
    db = next(get_db())
    try:
        if delete_account_backend(token, account_name, db):
            return "Account deleted successfully!"
        return "Account deletion failed."
    except Exception as e:
        return f"Failed to delete account: {str(e)}"


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
        raise gr.Error("Preset balance must be a number!")

    db = next(get_db())
    try:
        create_strategy(token, account_name, strategy_name, api_key, secret_key, passphrase, exchange_type,
                        preset_balance, db)
        return "Strategy added successfully!"
    except Exception as e:
        return f"Failed to add strategy: {str(e)}"


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
    print(account_name, strategy_name, api_key, secret_key, exchange_type, preset_balance)
    try:
        preset_balance = float(preset_balance)
    except ValueError:
        raise gr.Error("Preset balance must be a number!")

    db = next(get_db())
    if update_strategy_backend(token, account_name, strategy_name, api_key, secret_key, passphrase, exchange_type,
                               preset_balance, db):
        return "Strategy updated successfully!"
    return "Strategy update failed."


def delete_strategy(token, account_name, strategy_name):
    null_check(account_name, strategy_name)
    db = next(get_db())
    if delete_strategy_backend(token, account_name, strategy_name, db):
        return "Strategy deleted successfully!"
    return "Strategy deletion failed."


def validate_strategy(api_key, secret_key, passphrase, exchange_type):
    null_check(api_key, secret_key, passphrase, exchange_type)
    if validate_exchange_credentials(exchange_type, api_key, secret_key, passphrase):
        return "Credentials are valid!"
    return "Credentials are invalid!"


def add_user(token, name, login_token, linked_accounts):
    null_check(name, login_token)
    db = next(get_db())
    if create_user_backend(token, name, login_token, linked_accounts, db):
        return "User added successfully!"
    return f"Failed to add user!"


def update_selectable_users(token) -> gr.Dropdown:
    db = next(get_db())
    users = list_users_backend(token, db)
    return gr.Dropdown(choices=[user.name for user in users])


def remove_user(token, name):
    null_check(name)
    db = next(get_db())
    if delete_user_backend(token, name, db):
        return "User deleted successfully!"
    return "User deletion failed."


def update_user(token, name, login_token, linked_accounts):
    null_check(name, login_token)
    db = next(get_db())
    if update_user_backend(token, name, login_token, linked_accounts, db):
        return "User updated successfully!"
    return "User update failed."


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


def get_tables(token, date_ranges: Dict[str, Tuple[str, str]] = None):
    null_check(token)
    db = next(get_db())

    return get_tables_backend(token, date_ranges, db)


# Initialize Gradio interface
def admin_interface():
    session_token = gr.State("")  # Initialize empty session token

    with gr.Blocks() as admin_ui:
        with gr.Row():
            gr.Markdown("# Administration Panel")
            action_status = gr.Textbox(label="Action Status", value="Please login first!", text_align="right")
        gr.Markdown("## Login")
        with gr.Group():
            with gr.Row():
                master_token_input = gr.Textbox(label="Master Token", type="password", scale=3,
                                                value='20add5567250ccff972607fc1e516047')
                with gr.Column():
                    login_button = gr.Button("Login")
                    logout_button = gr.Button("Logout")

        gr.Markdown("## Account Management")
        with gr.Group(visible=False) as account_panel:
            with gr.Row():
                selected_account = gr.Dropdown(label="Select Accounts", choices=[], interactive=True)
                account_name_input = gr.Textbox(label="Account Name")
                start_date_input = gr.DateTime(label="Start Date", include_time=False)
                with gr.Column():
                    with gr.Row():
                        add_account_button = gr.Button("Add")
                        delete_account_button = gr.Button("Delete")
                    with gr.Row():
                        update_account_button = gr.Button("Update")

        gr.Markdown("### Strategy Management")
        with gr.Group(visible=False) as strategy_panel:
            with gr.Row():
                with gr.Column(scale=3):
                    with gr.Row():
                        selected_strategy = gr.Dropdown(
                            value='', label="Select Strategy", choices=['AI', 'DCA', 'CRYPTO', 'MARTINGALE'],
                            interactive=True)
                        preset_balance_input = gr.Textbox(label="Preset Balance")
                        exchange_type_input = gr.Dropdown(label="Exchange Type", choices=["bitget", "binance"],
                                                          interactive=True, allow_custom_value=False)
                    with gr.Row():
                        api_key_input = gr.Textbox(label="API Key")
                        secret_key_input = gr.Textbox(label="Secret Key", max_lines=1)
                        passphrase_input = gr.Textbox(label="Passphrase", type="password")
                with gr.Column():
                    add_strategy_button = gr.Button("Add")
                    update_strategy_button = gr.Button("Update")
                    delete_strategy_button = gr.Button("Delete")
                    validate_strategy_button = gr.Button("Validate")

        gr.Markdown("## User Management")
        with gr.Group(visible=False) as user_panel:
            with gr.Row():
                selected_user = gr.Dropdown(label="Select User", choices=[])
                user_name_input = gr.Textbox(label="User Name")
                login_token_input = gr.Textbox(label="Login Token")
                with gr.Column():
                    with gr.Row():
                        add_user_button = gr.Button("Add")
                        delete_user_button = gr.Button("Delete")
                    with gr.Row():
                        update_user_button = gr.Button("Update")

            linked_accounts = gr.CheckboxGroup(label="Linked Accounts", choices=[], interactive=True)

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


def user_interface():
    session_token = gr.State("")  # Initialize empty session token
    date_ranges = gr.State({})
    with gr.Blocks() as user_ui:
        with gr.Row():
            gr.Markdown("# User Panel")
            action_status = gr.Textbox(label="Action Status", value="Please login first!", text_align="right")
        gr.Markdown("## Login")
        with gr.Group():
            with gr.Row():
                login_token_input = gr.Textbox(label="Login Token", type="password", scale=3, value='abc')
                with gr.Column():
                    login_button = gr.Button("Login")
                    logout_button = gr.Button("Logout")

        @gr.render([date_ranges, session_token])
        def render_tables(date_range_list, token):
            if token and date_range_list:
                balance_tables = get_tables(token, date_range_list)
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
            gr.Markdown(lambda: f"## Summarized Account Balance `{datetime.now().strftime('%Y-%m-%d %H:%M')}`",
                        every=60.0)
            with gr.Row():
                gr.DataFrame(label="Total Balance", value=balance_tables["summarized"], show_label=False)
            gr.Markdown("## Account Details")
            with gr.Group():
                for i, account in enumerate(balance_tables["linked_accounts"]):
                    account_name = account['name']
                    account_df = account['data']
                    account_start_date = account['start_date']
                    history_df = account['history']['data']
                    start_date, end_date = account['history']['start_date'], account['history']['end_date']
                    with gr.Accordion(label=f"< {account_name} > since {account_start_date} ", open=False):
                        gr.DataFrame(value=account_df, show_label=False)
                        gr.Markdown("### Account Balance History")
                        with gr.Row():
                            start_date = gr.DateTime(
                                value=start_date, label="Start Date", include_time=False, interactive=True)
                            end_date = gr.DateTime(
                                value=end_date, label="End Date", include_time=False, interactive=True)
                            with gr.Column():
                                gr.Button('-', interactive=False)
                                reload_button = gr.Button("Reload")
                        gr.DataFrame(scale=4, value=history_df)

                    def _set_date_ranges(s, sd, ed):
                        sd = (datetime.fromtimestamp(sd)).strftime("%Y-%m-%d")
                        ed = (datetime.fromtimestamp(ed)).strftime("%Y-%m-%d")
                        return set_date_ranges(s, sd, ed, account_name)

                    reload_button.click(
                        _set_date_ranges, inputs=[session_token, start_date, end_date], outputs=[date_ranges])

    login_action = login_button.click(fn=user_login, inputs=[login_token_input], outputs=[session_token, action_status])
    login_action.then(fn=set_date_ranges, inputs=[session_token], outputs=[date_ranges])
    logout_action = logout_button.click(fn=logout, inputs=[session_token], outputs=[session_token, action_status])
    logout_action.then(fn=lambda: {}, outputs=[date_ranges])

    return user_ui


if __name__ == "__main__":
    with gr.Blocks() as app:
        gr.Markdown("# Asset Tracker App")
        with gr.Tab("User"):
            user_interface()
        with gr.Tab("Admin"):
            admin_interface()

    app.launch(inbrowser=True)
