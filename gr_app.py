import gradio as gr
from gr_backend import (
    admin_login, user_login, get_db,
    create_account, delete_account, update_account,
    create_user, delete_user, update_user,
    link_account_to_user, unlink_account_from_user,
    get_preset_balance_tables, get_realtime_balance_tables, sum_balance_tables,
    get_account_balance_history_tables
)
import pandas as pd

# Initialize Gradio interface
def admin_interface():
    def login(master_token):
        if admin_login(master_token):
            return "Admin login successful!"
        else:
            return "Admin login failed."

    def add_account(account_name, start_date):
        db = next(get_db())
        create_account(account_name, start_date, db)
        return "Account added successfully!"

    def remove_account(account_name):
        db = next(get_db())
        if delete_account(account_name, db):
            return "Account deleted successfully!"
        return "Account deletion failed."

    def modify_account(account_name, start_date):
        db = next(get_db())
        if update_account(account_name, start_date, db):
            return "Account updated successfully!"
        return "Account update failed."

    def add_user(name, login_token):
        db = next(get_db())
        create_user(name, login_token, db)
        return "User added successfully!"

    def remove_user(name):
        db = next(get_db())
        if delete_user(name, db):
            return "User deleted successfully!"
        return "User deletion failed."

    def modify_user(name, login_token):
        db = next(get_db())
        if update_user(name, login_token, db):
            return "User updated successfully!"
        return "User update failed."

    with gr.Blocks() as admin_ui:
        gr.Markdown("## Admin Login")
        master_token_input = gr.Textbox(label="Master Token")
        login_button = gr.Button("Login")
        login_output = gr.Textbox(label="Status")

        login_button.click(fn=login, inputs=[master_token_input], outputs=[login_output])

        gr.Markdown("## Account Management")
        account_name_input = gr.Textbox(label="Account Name")
        start_date_input = gr.Textbox(label="Start Date")
        add_account_button = gr.Button("Add Account")
        delete_account_button = gr.Button("Delete Account")
        update_account_button = gr.Button("Update Account")
        account_output = gr.Textbox(label="Account Status")

        add_account_button.click(fn=add_account, inputs=[account_name_input, start_date_input], outputs=[account_output])
        delete_account_button.click(fn=remove_account, inputs=[account_name_input], outputs=[account_output])
        update_account_button.click(fn=modify_account, inputs=[account_name_input, start_date_input], outputs=[account_output])

        gr.Markdown("## User Management")
        user_name_input = gr.Textbox(label="User Name")
        login_token_input = gr.Textbox(label="Login Token")
        add_user_button = gr.Button("Add User")
        delete_user_button = gr.Button("Delete User")
        update_user_button = gr.Button("Update User")
        user_output = gr.Textbox(label="User Status")

        add_user_button.click(fn=add_user, inputs=[user_name_input, login_token_input], outputs=[user_output])
        delete_user_button.click(fn=remove_user, inputs=[user_name_input], outputs=[user_output])
        update_user_button.click(fn=modify_user, inputs=[user_name_input, login_token_input], outputs=[user_output])

    return admin_ui


def user_interface():
    def login(login_token):
        db = next(get_db())
        if user_login(login_token, db):
            return "User login successful!"
        else:
            return "User login failed."

    def get_balances(user_name):
        db = next(get_db())
        preset_balances = get_preset_balance_tables(user_name, db)
        realtime_balances = get_realtime_balance_tables(user_name, db)
        summed_balances = sum_balance_tables(preset_balances + realtime_balances)

        # Create DataFrames for tables
        preset_df = pd.DataFrame(preset_balances)
        realtime_df = pd.DataFrame(realtime_balances)

        # Calculate differences and percentage differences
        realtime_df['Difference'] = realtime_df['realtime_balance'] - preset_df['preset_balance']
        realtime_df['Percentage Difference'] = (realtime_df['Difference'] / preset_df['preset_balance']) * 100

        # Prepare table footers
        preset_footer = f"Total Preset Balance: {summed_balances['total_preset_balance']}"
        realtime_footer = (f"Total Realtime Balance: {summed_balances['total_realtime_balance']}, "
                           f"Total Difference: {summed_balances['total_difference']}, "
                           f"Total Percentage Difference: {summed_balances['total_percentage_difference']}")

        return preset_df, preset_footer, realtime_df, realtime_footer

    def get_account_details(user_name, page_number=1):
        db = next(get_db())
        account_history = get_account_balance_history_tables(user_name, db, page_number)
        history_df = pd.DataFrame(account_history)
        return history_df

    with gr.Blocks() as user_ui:
        gr.Markdown("## User Login")
        login_token_input = gr.Textbox(label="Login Token")
        login_button = gr.Button("Login")
        login_output = gr.Textbox(label="Status")

        login_button.click(fn=login, inputs=[login_token_input], outputs=[login_output])

        gr.Markdown("## Dashboard")
        user_name_input = gr.Textbox(label="User Name")
        balance_button = gr.Button("Get Balances")
        preset_balance_table = gr.DataFrame(label="Preset Balance Table")
        preset_balance_footer = gr.Textbox(label="Preset Balance Footer")
        realtime_balance_table = gr.DataFrame(label="Realtime Balance Table")
        realtime_balance_footer = gr.Textbox(label="Realtime Balance Footer")

        balance_button.click(fn=get_balances, inputs=[user_name_input], 
                             outputs=[preset_balance_table, preset_balance_footer, 
                                      realtime_balance_table, realtime_balance_footer])

        gr.Markdown("## Account Details")
        page_number_input = gr.Slider(minimum=1, maximum=10, step=1, label="Page Number")
        account_details_button = gr.Button("Get Account Details")
        account_details_table = gr.DataFrame(label="Account Balance History Table")

        account_details_button.click(fn=get_account_details, inputs=[user_name_input, page_number_input], outputs=[account_details_table])

    return user_ui

# Main function to launch the Gradio app
def main():
    with gr.Blocks() as app:
        gr.Markdown("# Asset Tracker App")
        admin_ui = admin_interface()
        user_ui = user_interface()

        with gr.Tab("Admin"):
            admin_ui.render()
        with gr.Tab("User"):
            user_ui.render()

    app.launch()

if __name__ == "__main__":
    main()