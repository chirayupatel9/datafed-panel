from filebrowser import FileSelector
import panel as pn

files = FileSelector("~")

pn.Column(files).servable()
