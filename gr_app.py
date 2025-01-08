from typing import Tuple

import gradio as gr
import pandas as pd

from gr_backend import (admin_login, create_account, create_user, logout,
                        delete_account, delete_user,
                        get_account_balance_history_tables, get_db,
                        get_preset_balances, get_realtime_balances,
                        update_account, update_user, user_login)


# Initialize Gradio interface
def admin_interface():
    session_token = gr.State("")  # Initialize empty session token

    def login(master_token) -> Tuple[str, str]:
        token = admin_login(master_token)
        if not token:
            return "", "Login failed"
        return token, "Login successful!"

    def logout_(token) -> Tuple[str, str]:
        if logout(token):
            return "", "Logout successful!"
        return "", "Logout failed"

    def add_account(token, account_name, start_date):
        db = next(get_db())
        try:
            create_account(token, account_name, start_date, db)
            return "Account added successfully!"
        except Exception as e:
            return f"Failed to add account: {str(e)}"

    def remove_account(token, account_name):
        db = next(get_db())
        try:
            if delete_account(token, account_name, db):
                return "Account deleted successfully!"
            return "Account deletion failed."
        except Exception as e:
            return f"Failed to delete account: {str(e)}"

    def modify_account(token, account_name, start_date):
        db = next(get_db())
        try:
            if update_account(token, account_name, start_date, db):
                return "Account updated successfully!"
            return "Account update failed."
        except Exception as e:
            return f"Failed to update account: {str(e)}"

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

    with gr.Blocks() as admin_ui:
        gr.Markdown("## Admin Login")
        with gr.Row():
            login_output = gr.Textbox(label="Status", value="Please login first!")
            master_token_input = gr.Textbox(label="Master Token", type="password", scale=2)
            with gr.Column():
                login_button = gr.Button("Login")
                logout_button = gr.Button("Logout")

        login_button.click(fn=login, inputs=[master_token_input], outputs=[session_token, login_output])
        logout_button.click(fn=logout_, inputs=[session_token], outputs=[session_token, login_output])

        gr.Markdown("## Account Management")
        account_name_input = gr.Textbox(label="Account Name")
        start_date_input = gr.Textbox(label="Start Date (MM/DD/YYYY)")
        add_account_button = gr.Button("Add Account")
        delete_account_button = gr.Button("Delete Account")
        update_account_button = gr.Button("Update Account")
        account_output = gr.Textbox(label="Account Status")

        add_account_button.click(fn=add_account,
                                 inputs=[session_token, account_name_input, start_date_input],
                                 outputs=[account_output])
        delete_account_button.click(fn=remove_account,
                                    inputs=[session_token, account_name_input],
                                    outputs=[account_output])
        update_account_button.click(fn=modify_account,
                                    inputs=[session_token, account_name_input, start_date_input],
                                    outputs=[account_output])

        gr.Markdown("## User Management")
        user_name_input = gr.Textbox(label="User Name")
        login_token_input = gr.Textbox(label="Login Token")
        add_user_button = gr.Button("Add User")
        delete_user_button = gr.Button("Delete User")
        update_user_button = gr.Button("Update User")
        user_output = gr.Textbox(label="User Status")

        add_user_button.click(fn=add_user,
                              inputs=[session_token, user_name_input, login_token_input],
                              outputs=[user_output])
        delete_user_button.click(fn=remove_user,
                                 inputs=[session_token, user_name_input],
                                 outputs=[user_output])
        update_user_button.click(fn=modify_user,
                                 inputs=[session_token, user_name_input, login_token_input],
                                 outputs=[user_output])

    return admin_ui


def user_interface():
    session_token = gr.State("")  # Initialize empty session token

    def login(login_token):
        db = next(get_db())
        token = user_login(login_token, db)
        if not token:
            return "", "Login failed"
        return token, "Login successful!"

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

    with gr.Blocks() as user_ui:
        gr.Markdown("## User Login")
        login_token_input = gr.Textbox(label="Login Token", type="password")
        login_button = gr.Button("Login")
        login_output = gr.Textbox(label="Status", value="Please login first!")

        login_button.click(fn=login, inputs=[login_token_input], outputs=[session_token, login_output])

        gr.Markdown("## Dashboard")
        balance_button = gr.Button("Get Balances")
        preset_balance_table = gr.DataFrame(label="Preset Balance Table")
        preset_balance_footer = gr.Textbox(label="Preset Balance Footer")
        realtime_balance_table = gr.DataFrame(label="Realtime Balance Table")
        realtime_balance_footer = gr.Textbox(label="Realtime Balance Footer")

        balance_button.click(fn=get_balances,
                             inputs=[session_token],
                             outputs=[preset_balance_table, preset_balance_footer,
                                      realtime_balance_table, realtime_balance_footer])

        gr.Markdown("## Account Details")
        page_number_input = gr.Slider(minimum=1, maximum=10, step=1, label="Page Number", value=1)
        account_details_button = gr.Button("Get Account Details")
        account_details_table = gr.DataFrame(label="Account Balance History Table")

        account_details_button.click(fn=get_account_details,
                                     inputs=[session_token, page_number_input],
                                     outputs=[account_details_table])

    return user_ui


if __name__ == "__main__":
    with gr.Blocks() as app:
        gr.Markdown("# Asset Tracker App")
        with gr.Tab("Admin"):
            admin_interface()
        # with gr.Tab("User"):
        #     user_interface()

    app.launch(inbrowser=True)
