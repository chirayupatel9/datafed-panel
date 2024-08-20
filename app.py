from __future__ import annotations
import os
import json
import param
import panel as pn
from datafed.CommandLib import API
from panel.viewable import Layoutable

from panel.widgets.base import CompositeWidget
from panel.widgets.select import CrossSelector
from panel.layout import Column, Row, Divider
from panel.widgets.button import Button
from panel.widgets.input import TextInput
from panel.io import PeriodicCallback
from panel.util import fullpath
from fnmatch import fnmatch

pn.extension('material')

class FileSelector(CompositeWidget):
    directory = param.String(default=os.getcwd(), doc="The directory to explore.")
    file_pattern = param.String(default='*', doc="A glob-like pattern to filter the files.")
    only_files = param.Boolean(default=False, doc="Whether to only allow selecting files.")
    show_hidden = param.Boolean(default=False, doc="Whether to show hidden files and directories (starting with a period).")
    size = param.Integer(default=10, doc="The number of options shown at once (note this is the only way to control the height of this widget)")
    refresh_period = param.Integer(default=None, doc="If set to non-None value indicates how frequently to refresh the directory contents in milliseconds.")
    root_directory = param.String(default=None, doc="If set, overrides directory parameter as the root directory beyond which users cannot navigate.")
    value = param.List(default=[], doc="List of selected files.")
    _composite_type: ClassVar[type[Column]] = Column

    def __init__(self, directory=None, **params):
        if directory is not None:
            params['directory'] = fullpath(directory)
        if 'root_directory' in params:
            root = params['root_directory']
            params['root_directory'] = fullpath(root)
        if params.get('width') and params.get('height') and 'sizing_mode' not in params:
            params['sizing_mode'] = None

        super().__init__(**params)

        layout = {p: getattr(self, p) for p in Layoutable.param if p not in ('name', 'height', 'margin') and getattr(self, p) is not None}
        sel_layout = dict(layout, sizing_mode='stretch_width', height=300, margin=0)
        self._selector = CrossSelector(
            filter_fn=lambda p, f: fnmatch(f, p), size=self.size, **sel_layout, value=[]
        )

        self._back = Button(name='◀', width=40, height=40, margin=(5, 10, 0, 0), disabled=True, align='center')
        self._forward = Button(name='▶', width=40, height=40, margin=(5, 10, 0, 0), disabled=True, align='center')
        self._up = Button(name='⬆', width=40, height=40, margin=(5, 10, 0, 0), disabled=True, align='center')
        self._directory = TextInput(value=self.directory, margin=(5, 10, 0, 0), width_policy='max', height_policy='max')
        self._go = Button(name='⬇', disabled=True, width=40, height=40, margin=(5, 5, 0, 0), align='center')
        self._reload = Button(name='↻', width=40, height=40, margin=(5, 0, 0, 10), align='center')
        self._nav_bar = Row(
            self._back, self._forward, self._up, self._directory, self._go, self._reload,
            **dict(layout, width=None, margin=0, width_policy='max')
        )
        self._composite[:] = [self._nav_bar, Divider(margin=0), self._selector]

        self._stack = []
        self._cwd = None
        self._position = -1
        self._update_files(True)

        self._selector._lists[False].on_double_click(self._select_and_go)
        self.link(self._directory, directory='value')
        self._selector.param.watch(self._update_value, 'value')
        self._go.on_click(self._update_files)
        self._reload.on_click(self._update_files)
        self._up.on_click(self._go_up)
        self._back.on_click(self._go_back)
        self._forward.on_click(self._go_forward)
        self._directory.param.watch(self._dir_change, 'value')
        self._selector._lists[False].param.watch(self._select, 'value')
        self._selector._lists[False].param.watch(self._filter_denylist, 'options')
        self._periodic = PeriodicCallback(callback=self._refresh, period=self.refresh_period or 0)
        self.param.watch(self._update_periodic, 'refresh_period')
        if self.refresh_period:
            self._periodic.start()

        # Remove _json_viewer and replace with metadata_json_pane
        self._message = pn.pane.Markdown("Please select a JSON file", width_policy='max', height_policy='max')
        self._selected_file_display = pn.pane.Markdown("", width_policy='max', height_policy='max')
        self._output = pn.Column(self._selected_file_display,"<br>", self._message)

        # Modify layout to include just the metadata_json_pane or message
        self._composite.append(self._output)

    def _select_and_go(self, event):
        relpath = event.option.replace('📁', '').replace('⬆ ', '')
        if relpath == 'panel.':
            return self._go_up()
        sel = fullpath(os.path.join(self._cwd, relpath))
        if os.path.isdir(sel):
            self._directory.value = sel
        else:
            self._directory.value = self._cwd
        self._update_files()

    def _update_periodic(self, event):
        if event.new:
            self._periodic.period = event.new
            if not self._periodic.running:
                self._periodic.start()
        elif self._periodic.running:
            self._periodic.stop()

    @property
    def _root_directory(self):
        return self.root_directory or self.directory

    def _update_value(self, event):
        # Allow only one file to be selected
        if len(event.new) > 1:
            self._selector.value = [event.new[-1]]
        else:
            self._selector.value = event.new

        self.value = self._selector.value
        self._update_output(self.value)

    def _dir_change(self, event):
        path = fullpath(self._directory.value)
        if not path.startswith(self._root_directory):
            self._directory.value = self._root_directory
            return
        elif path != self._directory.value:
            self._directory.value = path
        self._go.disabled = path == self._cwd

    def _refresh(self):
        self._update_files(refresh=True)

    def _update_files(self, event=None, refresh=False):
        path = fullpath(self._directory.value)
        refresh = refresh or (event and getattr(event, 'obj', None) is self._reload)
        if refresh:
            path = self._cwd
        elif not os.path.isdir(path):
            self._selector.options = ['Entered path is not valid']
            self._selector.disabled = True
            return
        elif event is not None and (not self._stack or path != self._stack[-1]):
            self._stack.append(path)
            self._position += 1

        self._cwd = path
        if not refresh:
            self._go.disabled = True
        self._up.disabled = path == self._root_directory
        if self._position == len(self._stack)-1:
            self._forward.disabled = True
        if 0 <= self._position and len(self._stack) > 1:
            self._back.disabled = False

        selected = self.value
        dirs, files = self._scan_path(path, self.file_pattern)
        for s in selected:
            check = os.path.realpath(s) if os.path.islink(s) else s
            if os.path.isdir(check):
                dirs.append(s)
            elif os.path.isfile(check):
                files.append(s)

        paths = [
            p for p in sorted(dirs) + sorted(files)
            if self.show_hidden or not os.path.basename(p).startswith('.')
        ]
        abbreviated = [
            ('📁' if f in dirs else '') + os.path.relpath(f, self._cwd)
            for f in paths
        ]
        if not self._up.disabled:
            paths.insert(0, 'panel.')
            abbreviated.insert(0, '⬆ panel.')

        options = dict(zip(abbreviated, paths))
        self._selector.options = options
        self._selector.value = selected

    def _filter_denylist(self, event):
        dirs, files = self._scan_path(self._cwd, self.file_pattern)
        paths = [('📁' if p in dirs else '') + os.path.relpath(p, self._cwd) for p in dirs + files]
        denylist = self._selector._lists[False]
        options = dict(self._selector._items)
        self._selector.options.clear()
        prefix = [] if self._up.disabled else [('⬆ panel.', 'panel.')]
        self._selector.options.update(prefix + [
            (k, v) for k, v in options.items() if k in paths or v in self.value
        ])
        options = [o for o in denylist.options if o in paths]
        if not self._up.disabled:
            options.insert(0, '⬆ panel.')
        denylist.options = options

    def _select(self, event):
        if len(event.new) != 1:
            self._directory.value = self._cwd
            return

        relpath = event.new[0].replace('📁', '').replace('⬆ ', '')
        sel = fullpath(os.path.join(self._cwd, relpath))
        if os.path.isdir(sel):
            self._directory.value = sel
        else:
            self._directory.value = self._cwd

    def _go_back(self, event):
        self._position -= 1
        self._directory.value = self._stack[self._position]
        self._update_files()
        self._forward.disabled = False
        if self._position == 0:
            self._back.disabled = True

    def _go_forward(self, event):
        self._position += 1
        self._directory.value = self._stack[self._position]
        self._update_files()

    def _go_up(self, event=None):
        path = self._cwd.split(os.path.sep)
        self._directory.value = os.path.sep.join(path[:-1]) or os.path.sep
        self._update_files(True)

    def _update_output(self, selected_files):
        if not selected_files:
            self._selected_file_display.object = ""
            self._output[1:] = [self._message]
            return

        selected_file = selected_files[0]
        self._selected_file_display.object = f"**Selected File:** {selected_file}"

        if selected_file.endswith('.json'):
            with open(selected_file, 'r') as f:
                json_data = json.load(f)
            self._output[1:] = [self._selected_file_display, self._message]
            self.metadata_json_pane.object = json_data  # Update the metadata_json_pane
            self._output[1:] = [self.metadata_json_pane]
        else:
            self._output[1:] = [self._selected_file_display, self._message]

    def _scan_path(self, path, file_pattern):
        paths = [os.path.join(path, p) for p in os.listdir(path)]
        dirs = [p for p in paths if os.path.isdir(p)]
        files = [p for p in paths if os.path.isfile(p) and fnmatch(os.path.basename(p), file_pattern)]
        for p in paths:
            if not os.path.islink(p):
                continue
            path = os.path.realpath(p)
            if os.path.isdir(path):
                dirs.append(p)
            elif os.path.isfile(path):
                files.append(p)
        return dirs, files


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
    
    selected_context = param.Selector(objects={}, label="Select Context")
    available_contexts = param.Dict(default={}, label="Available Contexts")
    selected_collection = param.Selector(objects={}, label="Select Collection")
    available_collections = param.Dict(default={}, label="Available Collections")

    show_login_panel = param.Boolean(default=False)

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
        
        self.delete_button = pn.widgets.Button(name='Delete Record', button_type='danger')
        self.delete_button.on_click(self.delete_record)
        
        self.transfer_button = pn.widgets.Button(name='Transfer Data', button_type='primary')
        self.transfer_button.on_click(self.transfer_data)
        
        self.projects_button = pn.widgets.Button(name='View Projects', button_type='primary')
        self.projects_button.on_click(self.get_projects)

        self.logout_button = pn.widgets.Button(name='Logout', button_type='warning')
        self.logout_button.on_click(self.logout)

        self.projects_json_pane = pn.pane.JSON(object=None, name='Projects Output', depth=3, width=600, height=400)
        self.metadata_json_pane = pn.pane.JSON(object=None, name='Metadata', depth=3, width=600, height=400)
        self.record_output_pane = pn.pane.Markdown("**No output yet**", name='Record Output', width=600)

        # Replace FileUploadApp with FileSelector
        self.file_selector = FileSelector("/")
        self.file_selector.param.watch(self.update_metadata_from_file_selector, 'value')

        self.param.watch(self.update_collections, 'selected_context')
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
                self.login_status = "User in session!"
            else:
                self.current_user = "Not Logged In"
                self.current_context = "No Context"
        except Exception as e:
            self.login_status = f"Error: {e}"

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
            self.login_status = "Login Successful!"
            self.show_login_panel = False
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
        context_id = self.selected_context
 
        if context_id:
            collections = self.get_collections_in_context(context_id)
            self.available_collections = collections
            self.param['selected_collection'].objects = collections
            if collections:
                self.selected_collection = next(iter(collections))

    def get_collections_in_context(self, context):
        try:
            self.df_api.setContext(context)
            items_list = self.df_api.collectionItemsList('root', context=context)
            collections = {item.title: item.id for item in items_list[0].item if item.id.startswith("c/")}
            return collections
        except Exception as e:
            return [f"Error: {e}"]

    def update_metadata_from_file_selector(self, event):
        try:
            selected_file = event.new[0]
            if selected_file.endswith('.json'):
                with open(selected_file, 'r') as f:
                    file_content = json.load(f)
                self.metadata_json_pane.object = file_content
            else:
                self.metadata_json_pane.object = "Please select a JSON file."
        except json.JSONDecodeError as e:
            self.metadata_json_pane.object = f"Invalid JSON file: {e}"
        except Exception as e:
            self.metadata_json_pane.object = f"Error processing file: {e}"

    def create_record(self, event):
        if not self.title or not self.file_selector.value:
            self.record_output_pane.object = "**Error:** Title and metadata are required"
            return
        try:
            if self.selected_context:
                self.df_api.setContext(self.selected_context)
            response = self.df_api.dataCreate(
                title=self.title,
                metadata=json.dumps(self.metadata_json_pane.object),
                parent_id=self.available_collections[self.selected_collection] 
            )
            record_id = response[0].data[0].id
            self.record_output_pane.object = f"**Success:** Record created with ID {record_id}"
        except Exception as e:
            self.record_output_pane.object = f"**Error:** Failed to create record: {e}"

    def read_record(self, event):
        if not self.record_id:
            self.record_output_pane.object = "**Warning:** Record ID is required"
            return
        try:
            if self.selected_context:
                self.df_api.setContext(self.selected_context)
            response = self.df_api.dataView(f"d/{self.record_id}")
            res = self.to_dict(str(response[0].data[0]))
            self.record_output_pane.object = f"**Record Data:**\n\n```json\n{json.dumps(res, indent=2)}\n```"
        except Exception as e:
            self.record_output_pane.object = f"**Error:** Failed to read record: {e}"

    def update_record(self, event):
        if not self.record_id or not self.update_metadata:
            self.record_output_pane.object = "**Warning:** Record ID and metadata are required"
            return
        try:
            if self.selected_context:
                self.df_api.setContext(self.selected_context)
            response = self.df_api.dataUpdate(f"d/{self.record_id}", metadata=self.update_metadata)
            res = self.to_dict(str(response[0].data[0]))
            self.record_output_pane.object = f"**Success:** Record updated with new metadata"
        except Exception as e:
            self.record_output_pane.object = f"**Error:** Failed to update record: {e}"

    def delete_record(self, event):
        if not self.record_id:
            self.record_output_pane.object = "**Warning:** Record ID is required"
            return
        try:
            if self.selected_context:
                self.df_api.setContext(self.selected_context)
            self.df_api.dataDelete(f"d/{self.record_id}")
            self.record_output_pane.object = "**Success:** Record successfully deleted"
        except Exception as e:
            self.record_output_pane.object = f"**Error:** Failed to delete record: {e}"

    def transfer_data(self, event):
        if not self.source_id or not self.dest_collection:
            self.record_output_pane.object = "**Warning:** Source ID and destination collection are required"
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
            self.record_output_pane.object = f"**Success:** Data transferred to new record ID: {new_record_id}"
        except Exception as e:
            self.record_output_pane.object = f"**Error:** Failed to transfer data: {e}"

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
    pn.Param(app.param.login_status)
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
