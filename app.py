import panel as pn
from datafed_app import DataFedApp

app = DataFedApp()

header = pn.Row(
    pn.layout.HSpacer(),
    pn.pane.Markdown("**User:**"),
    pn.bind(lambda current_user: pn.pane.Markdown(f"**{current_user}**"), app.param.current_user),
    pn.layout.Spacer(width=20),
    app.login_button,
    pn.layout.Spacer(width=20),
    pn.pane.Markdown("**Context:**"),
    pn.bind(lambda current_context: pn.pane.Markdown(f"**{current_context}**"), app.param.current_context),
    pn.layout.Spacer(width=20),
    app.logout_button,
    pn.layout.HSpacer()
)

login_pane = pn.Column(
    pn.Param(app.param.username),
    pn.Param(app.param.password, widgets={'password': pn.widgets.PasswordInput}),
    pn.widgets.Button(name='Submit Login', button_type='primary', on_click=app.check_login),
    pn.Tabs(app.record_output_pane)
)

record_pane = pn.Column(
    pn.Param(app.param.selected_context, widgets={'selected_context': pn.widgets.Select}),
    pn.Param(app.param.selected_collection, widgets={'selected_collection': pn.widgets.Select}),
    pn.Tabs(
        ("Create Record", pn.Column(
            pn.Row(pn.Param(app.param.title), app.file_selector, app.metadata_json_pane),
            app.create_button, 
            app.record_output_pane
        )),
        ("Read Record", pn.Column(pn.Param(app.param.record_id), app.read_button, app.record_output_pane)),
        ("Update Record", pn.Column(pn.Param(app.param.record_id), pn.Param(app.param.update_metadata, widgets={'update_metadata': pn.widgets.TextAreaInput}), app.update_button, app.record_output_pane)),
        ("Delete Record", pn.Column(pn.Param(app.param.record_id), app.delete_button, app.record_output_pane)),
        ("Transfer Data", pn.Column(pn.Param(app.param.source_id), pn.Param(app.param.dest_collection), app.transfer_button, app.record_output_pane)),
    )
)

projects_pane = pn.Column(
    app.projects_button,
    app.projects_json_pane,
)

# Use MaterialTemplate for the layout
template = pn.template.MaterialTemplate(title='DataFed Management')

# Add content to the template
template.header.append(header)
template.main.append(
    pn.Tabs(
        ("Login", login_pane),
        ("Manage Records", record_pane),
        ("View Projects", projects_pane)
    )
)

# Conditionally show the login pane as a modal
template.modal.append(pn.bind(lambda show: login_pane if show else None, app.param.show_login_panel))

pn.state.onload(lambda: app.toggle_login_panel(None))  # Ensure modal can be triggered

template.servable()
