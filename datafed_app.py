from __future__ import annotations
import json
import param
import panel as pn
from datafed.CommandLib import API
from file_selector import FileSelector
from google.protobuf.json_format import MessageToJson
import os
from dotenv import load_dotenv

load_dotenv()
FILE_PATH = os.getenv("FILE_PATH")
pn.extension('material')
pn.extension('jsoneditor')

class DataFedApp(param.Parameterized):
    df_api = param.ClassSelector(class_=API, default=None)

    username = param.String(default="", label="Username")
    password = param.String(default="", label="Password")

    title = param.String(default="", label="Title")
    metadata = param.String(default="", label="Metadata (JSON format)")

    record_id = param.Selector(default=None, objects={}, label="Select Record")
    update_metadata = param.String(default="", label="Update Metadata (JSON format)")
    metadata_changed = param.Boolean(default=False, label="Metadata Changed")
    show_update_button = param.Boolean(default=False, label="Show Update Button")

    source_id = param.String(default="", label="Source ID")
    dest_collection = param.String(default="", label="Destination Collection")

    login_status = param.String(default="", label="Login Status")
    record_output = param.String(default="", label="Record Output")
    projects_output = param.String(default="", label="Projects Output")
    selected_project = param.String(default="", label="Selected Project")

    current_user = param.String(default="Not Logged In", label="Current User")
    current_context = param.String(default="No Context", label="Current Context")
    
    selected_context = param.Selector(default='root', objects={}, label="Select Context")
    available_contexts = param.Dict(default={}, label="Available Contexts")
    selected_collection = param.Selector(objects={}, label="Select Collection")
    available_collections = param.Dict(default={}, label="Available Collections")

    show_login_panel = param.Boolean(default=False)

    original_metadata = param.Dict(default={}, label="Original Metadata")  # To track the original metadata

    def __init__(self, **params):
        params['df_api'] = API() 
        super().__init__(**params)
        self.login_button = pn.widgets.Button(name='Login', button_type='primary')
        self.login_button.on_click(self.toggle_login_panel)
        
        self.create_button = pn.widgets.Button(name='Create Record', button_type='primary')
        self.create_button.on_click(self.create_record)
        
        self.read_button = pn.widgets.Button(name='Read Record', button_type='primary')
        self.read_button.on_click(self.read_record)
        
        self.update_button = pn.widgets.Button(name='Update Record', button_type='primary')
        self.update_button.on_click(self.update_record)
        self.update_button.visible = False  # Initially hidden
        
        self.delete_button = pn.widgets.Button(name='Delete Record', button_type='danger')
        self.delete_button.on_click(self.delete_record)
        
        self.transfer_button = pn.widgets.Button(name='Transfer Data', button_type='primary')
        self.transfer_button.on_click(self.transfer_data)
        
        self.projects_button = pn.widgets.Button(name='View Projects', button_type='primary')
        self.projects_button.on_click(self.get_projects)

        self.logout_button = pn.widgets.Button(name='Logout', button_type='warning')
        self.logout_button.on_click(self.logout)

        self.projects_json_pane = pn.pane.JSON(object=None, name='Projects Output', depth=3, width=600, height=400)
        self.metadata_json_editor = pn.widgets.JSONEditor(name='Metadata', width=600)
        self.record_output_pane = pn.pane.Markdown("<h3>Status Empty</h3>", name='Status', width=600)

        self.file_selector = FileSelector(FILE_PATH)
        self.file_selector.param.watch(self.update_metadata_from_file_selector, 'value')

        self.param.watch(self.update_collections, 'selected_context')
        self.metadata_json_editor.param.watch(self.on_metadata_change, 'value')
        self.param.watch(self.toggle_update_button_visibility, 'metadata_changed')

        pn.state.onload(self.initial_login_check)

    def initial_login_check(self):
        try:
            user_info = self.df_api.getAuthUser()
            if user_info:
                self.current_user = user_info
                self.current_context = self.df_api.getContext()
                ids, titles = self.get_available_contexts()
                self.available_contexts = {title: id_ for id_, title in zip(ids, titles)}
                self.param['selected_context'].objects = self.available_contexts
                self.selected_context = ids[0] if ids else None
                self.record_output_pane.object = "<h3>User in session!</h3>"
            else:
                self.current_user = "Not Logged In"
                self.current_context = "No Context"
        except Exception as e:
            self.record_output_pane.object = f"<h3>Error: {e}</h3>"

    def toggle_login_panel(self, event=None):
        self.show_login_panel = not self.show_login_panel  

    def check_login(self, event):
        try:
            self.df_api.loginByPassword(self.username, self.password)
            user_info = self.df_api.getAuthUser()
            if hasattr(user_info, 'username'):
                self.current_user = user_info.username
            else:
                self.current_user = str(user_info)
            self.current_context = self.df_api.getContext()
            ids, titles = self.get_available_contexts()
            self.available_contexts = {title: id_ for id_, title in zip(ids, titles)}
            self.param['selected_context'].objects = self.available_contexts
            self.selected_context = ids[0] if ids else None
            self.record_output_pane.object = "<h3>Login Successful!</h3>"
            self.show_login_panel = False
            self.update_records()
        except Exception as e:
            self.record_output_pane.object = f"<h3>Invalid username or password: {e}</h3>"

    def logout(self, event):
        self.df_api.logout()
        self.current_user = "Not Logged In"
        self.current_context = "No Context"
        self.record_output_pane.object = "<h3>Logged out successfully!</h3>"
        self.username = ""
        self.password = ""

    def update_collections(self, event):
        context_id = self.selected_context
 
        if context_id:
            collections = self.get_collections_in_context(context_id)
            self.available_collections = collections
            self.param['selected_collection'].objects = collections
            if collections:
                self.selected_collection = next(iter(collections))
            self.update_records()

    def get_collections_in_context(self, context):
        try:
            self.df_api.setContext(context)
            items_list = self.df_api.collectionItemsList('root', context=context)
            collections = {item.title: item.id for item in items_list[0].item if item.id.startswith("c/")}
            collections['root']='root'
            return collections
        except Exception as e:
            return [f"Error: {e}"]

    def update_metadata_from_file_selector(self, event):
        try:
            json_data = self.file_selector._update_output(self.file_selector.value)
            if json_data:
                self.metadata_json_editor.value = json_data
            else:
                self.metadata_json_editor.value = {}
        except json.JSONDecodeError as e:
            self.metadata_json_editor.value = {"error": f"Invalid JSON file: {e}"}
        except Exception as e:
            self.metadata_json_editor.value = {"error": f"Error processing file: {e}"}

    def create_record(self, event):
        if not self.title or not self.metadata_json_editor.value:
            self.record_output_pane.object = "<h3>Error: Title and metadata are required</h3>"
            return
        try:
            if self.selected_context:
                self.df_api.setContext(self.selected_context)
            response = self.df_api.dataCreate(
                title=self.title,
                metadata=json.dumps(self.metadata_json_editor.value),
                parent_id=self.available_collections[self.selected_collection] 
            )
            record_id = response[0].data[0].id
            self.record_output_pane.object = f"<h3>Success: Record created with ID {record_id}</h3>"
            self.update_records()
        except Exception as e:
            self.record_output_pane.object = f"<h3>Error: Failed to create record: {e}</h3>"

    def update_records(self):
        try:
            if not self.available_collections[self.selected_collection]:
                self.record_output_pane.object = "<h3>Warning: Context or Collection not selected</h3>"
                return
            
            items_list = self.df_api.collectionItemsList(coll_id=self.available_collections[self.selected_collection], context=self.selected_context)
            
            records = {item.title: item.id for item in items_list[0].item if item.id.startswith("d/")}
            
            self.param['record_id'].objects = records
            if records:
                self.record_id = next(iter(records))
            else:
                self.record_id = None
                self.record_output_pane.object = "<h3>No records found in the selected collection</h3>"
        
        except Exception as e:
            self.record_output_pane.object = f"<h3>Error: Failed to fetch records: {e}</h3>"

    def on_metadata_change(self, event):
        """Callback to handle changes in the JSON editor."""
        self.metadata_changed = True

    def toggle_update_button_visibility(self, event):
        """Toggle the visibility of the update button based on metadata changes."""
        self.update_button.visible = self.metadata_changed

    def read_record(self, event):
        if not self.record_id:
            self.record_output_pane.object = "<h3>Warning: Record ID is required</h3>"
            return
        try:            
            if self.selected_context:
                response = self.df_api.dataView(data_id=self.record_id, context=self.selected_context)
                res = MessageToJson(response[0])
                res_json = json.loads(res)

                for record in res_json.get('data', []):
                    if 'metadata' in record:
                        try:
                            record['metadata'] = json.loads(record['metadata'])
                        except json.JSONDecodeError:
                            pass

                self.original_metadata = res_json['data'][0]['metadata']
                self.metadata_json_editor.value = res_json
                self.metadata_changed = False  # Reset the change flag after loading

                self.record_output_pane.object = f"<h3>Record Data</h3>"
        except Exception as e:
            self.record_output_pane.object = f"<h3>Error: Failed to read record: {e}</h3>"

    def update_record(self, event=None):
        if not self.record_id or not self.metadata_json_editor.value:
            self.record_output_pane.object = "<h3>Warning: Record ID and metadata are required</h3>"
            return

        try:
            if self.selected_context and self.metadata_changed:
                self.df_api.setContext(self.selected_context)
                
                # Prepare parameters for the dataUpdate call
                update_params = {
                    'data_id': self.record_id,
                    'metadata': None,
                    'title': None,
                    'alias': None,
                    'description': None,
                    'tags': None,
                    'extension': None,
                    'schema': None,
                    'schema_enforce': None,
                    'deps_add': None,
                    'deps_rem': None,
                    'raw_data_file': None,
                    'context': self.selected_context
                }

                current_metadata = self.metadata_json_editor.value['data'][0]

                # Compare fields and populate update_params with changes
                if current_metadata.get('title') != self.original_metadata.get('title'):
                    update_params['title'] = current_metadata.get('title')

                if current_metadata.get('alias') != self.original_metadata.get('alias'):
                    update_params['alias'] = current_metadata.get('alias')

                if current_metadata.get('description') != self.original_metadata.get('description'):
                    update_params['description'] = current_metadata.get('description')

                if current_metadata.get('tags') != self.original_metadata.get('tags'):
                    update_params['tags'] = current_metadata.get('tags')

                if current_metadata.get('extension') != self.original_metadata.get('extension'):
                    update_params['extension'] = current_metadata.get('extension')

                if current_metadata.get('schema') != self.original_metadata.get('schema'):
                    update_params['schema'] = current_metadata.get('schema')

                if current_metadata.get('schema_enforce') != self.original_metadata.get('schema_enforce'):
                    update_params['schema_enforce'] = current_metadata.get('schema_enforce')

                if current_metadata.get('deps_add') != self.original_metadata.get('deps_add'):
                    update_params['deps_add'] = current_metadata.get('deps_add')

                if current_metadata.get('deps_rem') != self.original_metadata.get('deps_rem'):
                    update_params['deps_rem'] = current_metadata.get('deps_rem')

                if current_metadata.get('raw_data_file') != self.original_metadata.get('raw_data_file'):
                    update_params['raw_data_file'] = current_metadata.get('raw_data_file')

                # Check if metadata has changed
                updated_metadata = self.get_changed_fields(self.original_metadata.get('metadata', {}), current_metadata.get('metadata', {}))
                if updated_metadata:
                    update_params['metadata'] = json.dumps(updated_metadata)

                # Remove parameters that are None (not updated)
                update_params = {k: v for k, v in update_params.items() if v is not None}
                print(f"update_params:{update_params}")
                if update_params:
                    # Call the dataUpdate method with the updated parameters
                    response = self.df_api.dataUpdate(**update_params)
                    self.record_output_pane.object = f"<h3>Success: Record updated with new metadata</h3>"
                    self.metadata_changed = False  # Reset the change flag after updating
                else:
                    self.record_output_pane.object = f"<h3>No changes detected to update</h3>"
        except Exception as e:
            self.record_output_pane.object = f"<h3>Error: Failed to update record: {e}</h3>"

    def get_changed_fields(self, original: dict, current: dict) -> dict:
        """Compare original and current metadata, returning only changed fields."""
        changed_fields = {}
        for key, value in current.items():
            if key not in original or original[key] != value:
                changed_fields[key] = value
        return changed_fields

    def delete_record(self, event):
        if not self.record_id:
            self.record_output_pane.object = "<h3>Warning: Record ID is required</h3>"
            return
        try:
            if self.selected_context:
                self.df_api.setContext(self.selected_context)
            response = self.df_api.dataDelete(f"{self.record_id}")
            self.metadata_json_editor.value = {}  # Clear the JSON editor
            self.original_metadata = {}  # Reset the original metadata tracking
            self.record_output_pane.object = f"<h3>Success: Record :{self.record_id} successfully deleted  </h3>"
            self.update_records()
            self.record_id = None
        except Exception as e:
            self.record_output_pane.object = f"<h3>Error: Failed to delete record: {e}</h3>"

    def transfer_data(self, event):
        if not self.source_id or not self.dest_collection:
            self.record_output_pane.object = "<h3>Warning: Source ID and destination collection are required</h3>"
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
            self.record_output_pane.object = f"<h3>Success: Data transferred to new record ID: {new_record_id}</h3>"
        except Exception as e:
            self.record_output_pane.object = f"<h3>Error: Failed to transfer data: {e}</h3>"

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
            return [project.id for project in projects],[project.title for project in projects]
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
