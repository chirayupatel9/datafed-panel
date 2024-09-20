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

header0 = pn.Row(
    pn.layout.HSpacer(),
    pn.layout.Spacer(width=20),
    pn.layout.Spacer(width=20),
    pn.layout.HSpacer(),
    pn.config.raw_css.append("""
body {
    background-color: #0072B5;  /* Set the background color for the entire page */
}
.material-header {
    background-color: #0072B5;  /* Set the background color for the header */
}
.main-content {
    background-color: #0072B5;  /* Set background color for the main content */
}
""")
)

# Use param-based username and password
username_input = pn.Param(app.param.username, widgets={'username': pn.widgets.TextInput(placeholder='Enter your username', css_classes=['custom-input'])})
password_input = pn.Param(app.param.password, widgets={'password': pn.widgets.PasswordInput(placeholder='Enter your password', css_classes=['custom-input'])})

username_label = pn.pane.Markdown("<span class='custom-label'>**Username**</span>")
password_label = pn.pane.Markdown("<span class='custom-label'>**Password**</span>")



# Define the login pane
login_pane = pn.Column(
    username_label,
    username_input,
    password_label,
    password_input,
    pn.widgets.Button(name='Submit Login', button_type='primary', on_click=app.check_login),
    css_classes=['centered-content']  # Apply CSS classes for styling
)


# Custom CSS for styling the login pane
pn.config.raw_css.append("""
.centered-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    min-height: 80vh;
    padding-left: 20%;
}
body {
    margin: 0;
}
.custom-label {
    color: #FFFFFF; /* Label color */
    font-size: 15px; /* Label font size */
    display: block; /* Ensures label takes up its own line */
    margin-bottom: -10px; /* Control the space between the label and the input */
}
.custom-input {
    margin-top: 0; /* Ensure no extra space above the input */
    margin-bottom: 12px; /* Control space between the input and the next element */
    color: #FFFFFF; /* Input text color */
    padding: 5px;
}

""")


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

@pn.depends(app.param.current_user)
def header_content(current_user):
    if current_user == "Not Logged In":
        return header0
    else:
        return header



# Use MaterialTemplate for the layout
template = pn.template.MaterialTemplate(title='DataFed Management')

# Add content to the template
template.header.append(header_content)
template.main.append(main_content)  # Append the main content function directly

# Conditionally show the login pane as a modal
template.modal.append(pn.bind(lambda show: login_pane if show else None, app.param.show_login_panel))

pn.state.onload(lambda: app.toggle_login_panel(None))  # Ensure modal can be triggered

template.servable()
