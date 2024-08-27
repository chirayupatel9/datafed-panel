import panel as pn
from datafed_app import DataFedApp

app = DataFedApp()

@pn.depends(app.param.current_user)
def login_logout_button(current_user):
    if current_user == "Not Logged In":
        return app.login_button  # Show login button if not logged in
    else:
        return app.logout_button  # Show logout button if logged in
@pn.depends(app.metadata_json_editor.param.value)
def update_button_visibility(metadata_json_editor_value):
    if metadata_json_editor_value:  # If there's content in the editor
        return app.update_button  # Show the update button
    else:
        return pn.pane.Markdown("") 
# Define the header
header = pn.Row(
    pn.layout.HSpacer(),
    pn.pane.Markdown("**User:**"),
    pn.bind(lambda current_user: pn.pane.Markdown(f"**{current_user}**"), app.param.current_user),
    pn.layout.Spacer(width=20),
    app.logout_button,
    pn.layout.Spacer(width=20),
    pn.layout.HSpacer()
)

# Define the login pane
login_pane = pn.Column(
    pn.Param(app.param.username),
    pn.Param(app.param.password, widgets={'password': pn.widgets.PasswordInput}),
    pn.widgets.Button(name='Submit Login', button_type='primary', on_click=app.check_login),
    pn.Param(app.param.login_status)
)

# Define the record management pane
record_pane = pn.Column(
    pn.Param(app.param.selected_context, widgets={'selected_context': pn.widgets.Select}),
    pn.Param(app.param.selected_collection, widgets={'selected_collection': pn.widgets.Select}),
    pn.Tabs(
        ("Create Record", pn.Column(
            pn.Row(pn.Param(app.param.title), app.file_selector, app.metadata_json_editor),  # Updated here
            app.create_button, 
            app.record_output_pane
        )),
        ("Read Record", pn.Column(pn.Param(app.param.record_id), pn.Column(app.read_button,app.update_button,app.delete_button,), app.record_output_pane,app.metadata_json_editor)),
        
        )
)

# conflict commit ("Transfer Data", pn.Column(pn.Param(app.param.source_id), pn.Param(app.param.dest_collection), app.transfer_button, app.record_output_pane)),
# Dynamically show the login pane or the record management pane based on login status
@pn.depends(app.param.current_user)
def main_content(current_user):
    if current_user == "Not Logged In":
        return login_pane
    else:
        return record_pane


# Use MaterialTemplate for the layout
template = pn.template.MaterialTemplate(title='DataFed Management')

# Add content to the template
template.header.append(header)
template.main.append(main_content)  # Append the main content function directly

# Conditionally show the login pane as a modal
template.modal.append(pn.bind(lambda show: login_pane if show else None, app.param.show_login_panel))

pn.state.onload(lambda: app.toggle_login_panel(None))  # Ensure modal can be triggered

template.servable()
