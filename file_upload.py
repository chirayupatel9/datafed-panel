import panel as pn
import param
import json

pn.extension()

class FileUploadApp(param.Parameterized):
    file_input = param.ClassSelector(class_=pn.widgets.FileInput, default=pn.widgets.FileInput(accept='.json'))
    file_content = param.String(default="", label="File Content")

    def __init__(self, **params):
        super().__init__(**params)
        self.file_input.param.watch(self._file_input_handler, 'value')

    def _file_input_handler(self, event):
        if event.new:
            file_content = event.new
            try:
                file_json = json.loads(file_content.decode('utf-8'))
                self.file_content = json.dumps(file_json, indent=2)
            except json.JSONDecodeError:
                self.file_content = "Invalid JSON file"

    def view(self):
        return pn.Column(
            pn.pane.Markdown("### Drag and Drop JSON File Upload"),
            self.file_input,
            pn.pane.Markdown("### File Content Preview"),
            # pn.pane.JSON(self.file_content, depth=3, width=600, height=400)
        )

file_upload_app = FileUploadApp()
file_upload_app_view = file_upload_app.view()
