import panel as pn
import param
import json
from datafed.CommandLib import API

pn.extension()

class DataFedApp(param.Parameterized):
    df_api = param.ClassSelector(class_=API, default=None)

    username = param.String(default="", label="Username")
    password = param.String(default="", label="Password")

    title = param.String(default="", label="Title")
    metadata = param.String(default="", label="Metadata (JSON format)")

    record_id = param.String(default="", label="Record ID")
    update_metadata = param.String(default="", label="Update Metadata (JSON format)")

    source_id = param.String(default="", label="Source ID")
    dest_collection = param.String(default="", label="Destination Collection")

    login_status = param.String(default="", label="Login Status")
    record_output = param.String(default="", label="Record Output")
    projects_output = param.String(default="", label="Projects Output")
    selected_project = param.String(default="", label="Selected Project")

    current_user = param.String(default="Not Logged In", label="Current User")
    current_context = param.String(default="No Context", label="Current Context")
    available_contexts = param.List(default=[], label="Available Contexts")

    selected_context = param.Selector(objects=[], label="Select Context")
    available_collections = param.List(default=[], label="Available Collections")
    selected_collection = param.Selector(objects=[], label="Select Collection")

    def __init__(self, **params):
        params['df_api'] = API()  # Initialize df_api here to avoid pickling issues
        super().__init__(**params)
        self.login_button = pn.widgets.Button(name='Login', button_type='primary')
        self.login_button.on_click(self.check_login)
        
        self.create_button = pn.widgets.Button(name='Create Record', button_type='primary')
        self.create_button.on_click(self.create_record)
        
        self.read_button = pn.widgets.Button(name='Read Record', button_type='primary')
        self.read_button.on_click(self.read_record)
        
        self.update_button = pn.widgets.Button(name='Update Record', button_type='primary')
        self.update_button.on_click(self.update_record)
        
        self.delete_button = pn.widgets.Button(name='Delete Record', button_type='danger')
        self.delete_button.on_click(self.delete_record)
        
        self.transfer_button = pn.widgets.Button(name='Transfer Data', button_type='primary')
        self.transfer_button.on_click(self.transfer_data)
        
        self.projects_button = pn.widgets.Button(name='View Projects', button_type='primary')
        self.projects_button.on_click(self.get_projects)

        self.logout_button = pn.widgets.Button(name='Logout', button_type='warning')
        self.logout_button.on_click(self.logout)

        self.projects_json_pane = pn.pane.JSON(object=None, name='Projects Output', depth=3, width=600, height=400)

        self.param.watch(self.update_collections, 'selected_context')

    def check_login(self, event):
        try:
            self.df_api.loginByPassword(self.username, self.password)
            user_info = self.df_api.getAuthUser()
            if hasattr(user_info, 'username'):
                self.current_user = user_info.username
            else:
                self.current_user = str(user_info)
            self.current_context = self.df_api.getContext()
            self.available_contexts = self.get_available_contexts()
            self.param['selected_context'].objects = self.available_contexts
            self.selected_context = self.available_contexts[0] if self.available_contexts else None
            print(f"Available contexts after login: {self.available_contexts}")  # Debug print
            self.login_status = "Login Successful!"
        except Exception as e:
            self.login_status = f"Invalid username or password: {e}"

    def logout(self, event):
        self.df_api.logout()
        self.current_user = "Not Logged In"
        self.current_context = "No Context"
        self.login_status = "Logged out successfully!"
        self.username = ""
        self.password = ""

    def update_collections(self, event):
        if self.selected_context:
            collections = self.get_collections_in_context(self.selected_context)
            self.param['selected_collection'].objects = collections
            if collections:
                self.selected_collection = collections[0]
            print(f"Available collections for {self.selected_context}: {collections}")  # Debug print

    def get_collections_in_context(self, context):
        try:
            self.df_api.setContext(context)
            response = self.df_api.collectionView('root', context=context)
            print(f"Root collection details: {response}")  # Debug print
            items_list = self.df_api.collectionItemsList('root', context=context)
            collections = [item.id for item in items_list[0].item]
            print(f'collections: {collections}')
            return collections
        except Exception as e:
            return [f"Error: {e}"]

    def create_record(self, event):
        if not self.title or not self.metadata:
            self.record_output = "Title and metadata are required"
            return
        try:
            if self.selected_context:
                self.df_api.setContext(self.selected_context)
            print(f"self.selected_collection:{self.selected_collection[2:]}")
            response = self.df_api.dataCreate(self.title, metadata=self.metadata, parent_id=self.selected_collection)
            res = self.to_dict(str(response[0].data[0]))
            self.record_output = f"Record created: {res}"
        except Exception as e:
            self.record_output = f"Failed to create record: {e}"

    def read_record(self, event):
        if not self.record_id:
            self.record_output = "Record ID is required"
            return
        try:
            if self.selected_context:
                self.df_api.setContext(self.selected_context)
            response = self.df_api.dataView(f"d/{self.record_id}")
            res = self.to_dict(str(response[0].data[0]))
            self.record_output = str(res)
        except Exception as e:
            self.record_output = f"Failed to read record: {e}"

    def update_record(self, event):
        if not self.record_id or not self.update_metadata:
            self.record_output = "Record ID and metadata are required"
            return
        try:
            if self.selected_context:
                self.df_api.setContext(self.selected_context)
            response = self.df_api.dataUpdate(f"d/{self.record_id}", metadata=self.update_metadata)
            res = self.to_dict(str(response[0].data[0]))
            self.record_output = f"Record updated: {res}"
        except Exception as e:
            self.record_output = f"Failed to update record: {e}"

    def delete_record(self, event):
        if not self.record_id:
            self.record_output = "Record ID is required"
            return
        try:
            if self.selected_context:
                self.df_api.setContext(self.selected_context)
            self.df_api.dataDelete(f"d/{self.record_id}")
            self.record_output = "Record successfully deleted"
        except Exception as e:
            self.record_output = f"Failed to delete record: {e}"

    def transfer_data(self, event):
        if not self.source_id or not self.dest_collection:
            self.record_output = "Source ID and destination collection are required"
            return
        try:
            if self.selected_context:
                self.df_api.setContext(self.selected_context)
            source_record = self.df_api.dataView(f"d/{self.source_id}")
            source_details = source_record[0].data[0]
            new_record = self.df_api.dataCreate(
                title=source_details.title,
                metadata=source_details.metadata,
                parent=self.dest_collection
            )
            new_record_id = new_record[0].data[0].id
            self.df_api.dataMove(f"d/{self.source_id}", new_record_id)
            self.record_output = f"Data transferred to new record ID: {new_record_id}"
        except Exception as e:
            self.record_output = f"Failed to transfer data: {e}"

    def get_projects(self, event):
        try:
            response = self.df_api.projectList()
            projects = response[0].item
            projects_list = [{"id": project.id, "title": project.title} for project in projects]
            self.projects_json_pane.object = projects_list
        except Exception as e:
            self.projects_json_pane.object = {"error": str(e)}

    def get_available_contexts(self):
        try:
            response = self.df_api.projectList()
            projects = response[0].item
            return [project.id for project in projects]
        except Exception as e:
            return [f"Error: {e}"]

    def to_dict(self, data_str):
        data_dict = {}
        for line in data_str.strip().split('\n'):
            key, value = line.split(": ", 1)
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value == 'true':
                value = True
            elif value == 'false':
                value = False
            elif value.isdigit():
                value = int(value)
            data_dict[key] = value
        return data_dict

app = DataFedApp()

header = pn.Row(
    pn.layout.HSpacer(),
    pn.pane.Markdown("**User:**"),
    pn.bind(lambda current_user: pn.pane.Markdown(f"**{current_user}**"), app.param.current_user),
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
    app.login_button,
    pn.Param(app.param.login_status)
)

record_pane = pn.Column(
    pn.Param(app.param.selected_context, widgets={'selected_context': pn.widgets.Select}),
    pn.Param(app.param.selected_collection, widgets={'selected_collection': pn.widgets.Select}),
    pn.Tabs(
        ("Create Record", pn.Column(pn.Param(app.param.title), pn.Param(app.param.metadata), app.create_button, pn.Param(app.param.record_output))),
        ("Read Record", pn.Column(pn.Param(app.param.record_id), app.read_button, pn.Param(app.param.record_output))),
        ("Update Record", pn.Column(pn.Param(app.param.record_id), pn.Param(app.param.update_metadata), app.update_button, pn.Param(app.param.record_output))),
        ("Delete Record", pn.Column(pn.Param(app.param.record_id), app.delete_button, pn.Param(app.param.record_output))),
        ("Transfer Data", pn.Column(pn.Param(app.param.source_id), pn.Param(app.param.dest_collection), app.transfer_button, pn.Param(app.param.record_output))),
    )
)

projects_pane = pn.Column(
    app.projects_button,
    app.projects_json_pane,
)

main_pane = pn.Column(
    header,
    pn.Tabs(
        ("Login", login_pane),
        ("Manage Records", record_pane),
        ("View Projects", projects_pane)
    )
)

main_pane.servable()
