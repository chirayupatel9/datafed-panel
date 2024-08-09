import panel as pn
import param
import json

pn.extension('material')

class FileUploadApp(param.Parameterized):
    file_input = param.ClassSelector(class_=pn.widgets.FileInput)
    file_content = param.String(default="", doc="Contents of the uploaded file")

    def __init__(self, **params):
        super().__init__(**params)
        self.file_input = pn.widgets.FileInput(
            accept='.json',
            multiple=False,
            css_classes=['material-input'],
            width=400,  # Adjusted width
            height=200  # Adjusted height
        )
        self.file_input.param.watch(self._handle_file_upload, 'value')

    def _handle_file_upload(self, event):
        if self.file_input.value is not None:
            file_bytes = self.file_input.value
            try:
                file_content = file_bytes.decode('utf-8')
                self.file_content = file_content
            except Exception as e:
                self.file_content = f"Error decoding file: {e}"

    def view(self):
        return pn.Card(
            pn.pane.HTML("<h2 style='text-align: center;'>Drag and Drop your JSON file here</h2>"),
            self.file_input,
            title="File Upload",
            css_classes=['material-card'],
            margin=(20, 20),
            width=450,  # Adjusted width to match content
            height=300  # Adjusted height to provide enough space
        )

file_upload_app = FileUploadApp()
file_upload_app_view = file_upload_app.view()
