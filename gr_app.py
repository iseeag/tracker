from datetime import datetime
from typing import List, Tuple

import gradio as gr
import pandas as pd

from gr_backend import (admin_login, create_account, create_user,
                        delete_account, delete_user,
                        get_account_balance_history_tables, get_db,
                        get_preset_balances, get_realtime_balances,
                        list_accounts, get_account, create_strategy)
from gr_backend import logout as user_logout_backend
from gr_backend import update_account, update_user
from gr_backend import user_login as user_login_backend
from gr_backend import get_strategy as get_strategy_backend
from gr_backend import update_strategy as update_strategy_backend
from gr_backend import delete_strategy as delete_strategy_backend


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


def remove_account(token, account_name):
    null_check(account_name)
    db = next(get_db())
    try:
        if delete_account(token, account_name, db):
            return "Account deleted successfully!"
        return "Account deletion failed."
    except Exception as e:
        return f"Failed to delete account: {str(e)}"


def update_selectable_accounts(token) -> gr.Dropdown:
    if not token:
        return gr.Dropdown(choices=[])
    db = next(get_db())
    accounts = list_accounts(token, db)
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


# ######### ui react ###########
def toggle_panels_x3(token):
    visible = True if token else True  # todo: fix this
    return [gr.Group(visible=visible) for _ in range(3)]


def toggle_panels_x2(token):
    visible = True if token else True  # todo: fix this
    return [gr.Group(visible=visible) for _ in range(2)]


def clear_account_panel():
    return gr.Dropdown(value=''), gr.Textbox(value=''), gr.DateTime(value=None)


def fill_account(token, account_name):
    db = next(get_db())
    account = get_account(token, account_name, db)
    return gr.Textbox(value=account.account_name), gr.DateTime(value=account.start_date.strftime("%Y-%m-%d"))


def add_user(token, name, login_token):
    db = next(get_db())
    try:
        create_user(token, name, login_token, db)
        return "User added successfully!"
    except Exception as e:
        return f"Failed to add user: {str(e)}"


def remove_user(token, name):
    db = next(get_db())
    try:
        if delete_user(token, name, db):
            return "User deleted successfully!"
        return "User deletion failed."
    except Exception as e:
        return f"Failed to delete user: {str(e)}"


def modify_user(token, name, login_token):
    db = next(get_db())
    try:
        if update_user(token, name, login_token, db):
            return "User updated successfully!"
        return "User update failed."
    except Exception as e:
        return f"Failed to update user: {str(e)}"

    def get_balances(token):
        db = next(get_db())
        try:
            preset_balances = get_preset_balances(token, db)
            realtime_balances = get_realtime_balances(token, db)

            # Create DataFrames for tables
            preset_df = pd.DataFrame(preset_balances)
            realtime_df = pd.DataFrame(realtime_balances)

            # Calculate differences and percentage differences
            if not preset_df.empty and not realtime_df.empty:
                realtime_df['Difference'] = realtime_df['realtime_balance'] - preset_df['preset_balance']
                realtime_df['Percentage Difference'] = (realtime_df['Difference'] / preset_df['preset_balance']) * 100

                # Prepare table footers
                total_preset = preset_df['preset_balance'].sum()
                total_realtime = realtime_df['realtime_balance'].sum()
                total_diff = total_realtime - total_preset
                total_pct_diff = (total_diff / total_preset) * 100 if total_preset != 0 else 0

                preset_footer = f"Total Preset Balance: {total_preset:.2f}"
                realtime_footer = (f"Total Realtime Balance: {total_realtime:.2f}, "
                                   f"Total Difference: {total_diff:.2f}, "
                                   f"Total Percentage Difference: {total_pct_diff:.2f}%")
            else:
                preset_footer = "No data available"
                realtime_footer = "No data available"

            return preset_df, preset_footer, realtime_df, realtime_footer
        except Exception as e:
            return pd.DataFrame(), f"Error: {str(e)}", pd.DataFrame(), f"Error: {str(e)}"

    def get_account_details(token, page_number=1):
        db = next(get_db())
        try:
            account_history = get_account_balance_history_tables(token, db, page_number)
            history_df = pd.DataFrame(account_history)
            return history_df
        except Exception as e:
            return pd.DataFrame(), f"Error: {str(e)}"


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
                        secret_key_input = gr.Textbox(label="Secret Key")
                        passphrase_input = gr.Textbox(label="Passphrase", type="password")
                with gr.Column():
                    add_strategy_button = gr.Button("Add")
                    update_strategy_button = gr.Button("Update")
                    delete_strategy_button = gr.Button("Delete")
                    validate_strategy_button = gr.Button("Validate")

        gr.Markdown("## User Management")
        with gr.Group(visible=False) as user_panel:
            with gr.Row():
                select_user = gr.Dropdown(label="Select User", choices=[])
                user_name_input = gr.Textbox(label="User Name")
                login_token_input = gr.Textbox(label="Login Token")
                with gr.Column():
                    with gr.Row():
                        add_user_button = gr.Button("Add")
                        delete_user_button = gr.Button("Delete")
                    with gr.Row():
                        update_user_button = gr.Button("Update")

            gr.CheckboxGroup(label="Select Accounts", choices=[])

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
            fn=remove_account, inputs=[session_token, selected_account], outputs=[action_status])
        update_account_button.click(
            fn=modify_account, inputs=[session_token, account_name_input, start_date_input], outputs=[action_status])
        for a in [login_action, add_acc_action, delete_acc_action]:
            a.then(update_selectable_accounts, inputs=[session_token], outputs=[selected_account])
        for a in [add_acc_action, delete_acc_action]:
            a.then(clear_account_panel, outputs=[selected_account, account_name_input, start_date_input])
        selected_account.select(
            fill_account, inputs=[session_token, selected_account], outputs=[account_name_input, start_date_input])
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
        validate_strategy_button.click()
        selected_strategy.select(get_strategy, inputs=[session_token, selected_account, selected_strategy], outputs=[
            api_key_input, secret_key_input, passphrase_input, exchange_type_input, preset_balance_input])

        # ---- user ----
        add_user_button.click(fn=add_user,
                              inputs=[session_token, user_name_input, login_token_input],
                              outputs=[action_status])
        delete_user_button.click(fn=remove_user,
                                 inputs=[session_token, user_name_input],
                                 outputs=[action_status])
        update_user_button.click(fn=modify_user,
                                 inputs=[session_token, user_name_input, login_token_input],
                                 outputs=[action_status])

    return admin_ui


def user_interface():
    session_token = gr.State("")  # Initialize empty session token

    with gr.Blocks() as user_ui:
        with gr.Row():
            gr.Markdown("# User Panel")
            action_status = gr.Textbox(label="Action Status", value="Please login first!", text_align="right")
        gr.Markdown("## Login")
        with gr.Group():
            with gr.Row():
                login_token_input = gr.Textbox(label="Login Token", type="password", scale=3)
                with gr.Column():
                    login_button = gr.Button("Login")
                    logout_button = gr.Button("Logout")

        gr.Markdown("## Summarized Account Balance")
        with gr.Row(visible=False) as account_balance_panel:
            preset_balance_table = gr.DataFrame(
                scale=2,
                label="Total Initial Balance",
                value=pd.DataFrame([['alksdjfl', 9384093, ], ['slkdjfs', 33948]],
                                   columns=["Account Name", "Preset Balance"]))
            realtime_balance_table = gr.DataFrame(
                scale=4,
                label="Total Realtime Balance",
                value=pd.DataFrame([['alksdjfl', 9384093, 39, 30], ['slkdjfs', 33948, 30, 89],
                                    ['3lksdj', 230983, 39, 30], ['Total', 20390, 30, 30]],
                                   columns=["Account Name", "Realtime Balance", "Difference", "Percentage Difference"]))

        gr.Markdown("## Account Details")
        preset_tables = []
        realtime_tables = []
        history_tables = []
        with gr.Group(visible=False) as account_details_panel:
            for i in range(3):
                with gr.Accordion(label=f"A Account", open=False):
                    with gr.Row():
                        preset_balance_table = gr.DataFrame(
                            scale=2,
                            label="Total Initial Balance",
                            value=pd.DataFrame([['alksdjfl', 9384093, ], ['slkdjfs', 33948]],
                                               columns=["Account Name", "Preset Balance"]))
                        realtime_balance_table = gr.DataFrame(
                            scale=4,
                            label="Total Realtime Balance",
                            value=pd.DataFrame([['alksdjfl', 9384093, 39, 30], ['slkdjfs', 33948, 30, 89],
                                                ['3lksdj', 230983, 39, 30], ['Total', 20390, 30, 30]],
                                               columns=["Account Name", "Realtime Balance", "Difference",
                                                        "Percentage Difference"]))
                        preset_tables.append(preset_balance_table)
                        realtime_tables.append(realtime_balance_table)
                    history_table = gr.DataFrame(
                        scale=4,
                        label="Account Balance History",
                        value=pd.DataFrame(
                            [["2021-01-01", 9384093, 9384093, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]],
                            columns=["Date", "S1", "S2", "S3", "Total", "Diff1", "Diff2", "Diff3", "Total Diff",
                                     "Pct Diff1", "Pct Diff2", "Pct Diff3", "Total Pct Diff"]))
                    history_tables.append(history_table)
                    with gr.Row():
                        previous_page_button = gr.Button("Previous Page")
                        next_page_button = gr.Button("Next Page")

    login_button.click(fn=user_login, inputs=[login_token_input], outputs=[session_token, action_status])
    logout_button.click(fn=logout, inputs=[session_token], outputs=[session_token, action_status])
    session_token.change(fn=toggle_panels_x2, inputs=[session_token],
                         outputs=[account_balance_panel, account_details_panel])

    return user_ui


if __name__ == "__main__":
    with gr.Blocks() as app:
        gr.Markdown("# Asset Tracker App")
        with gr.Tab("Admin"):
            admin_interface()
        with gr.Tab("User"):
            user_interface()

    app.launch(inbrowser=True)
