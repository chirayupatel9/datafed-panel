import panel as pn
from filebrowser import FileSelector

files = FileSelector('~').servable()
