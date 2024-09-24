import os
import json
import mimetypes
from PIL import Image
from PyPDF2 import PdfReader
from mutagen import File as MutagenFile

def get_file_metadata(file_path):
    """
    Determines the file type and returns the corresponding metadata as a dictionary.
    """
    file_type, _ = mimetypes.guess_type(file_path)
    
    if file_type:
        if file_type.startswith('image'):
            return get_image_metadata(file_path)
        elif file_type == 'application/pdf':
            return get_pdf_metadata(file_path)
        elif file_type == 'application/json':
            return get_json_metadata(file_path)
        else:
            return get_generic_metadata(file_path)
    else:
        return get_generic_metadata(file_path)

def get_image_metadata(file_path):
    try:
        with Image.open(file_path) as img:
            return {
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                # 'info': img.info,
            }
    except Exception as e:
        return {'error': str(e)}

def get_pdf_metadata(file_path):
    try:
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            metadata = reader.metadata
            return {k[1:]: v for k, v in metadata.items()}
    except Exception as e:
        return {'error': str(e)}

def get_json_metadata(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {'error': str(e)}

def get_generic_metadata(file_path):
    try:
        file_stats = os.stat(file_path)
        return {
            'size': file_stats.st_size,
            'last_modified': file_stats.st_mtime,
            'last_accessed': file_stats.st_atime,
            'creation_time': file_stats.st_ctime,
            'filename': os.path.basename(file_path),
        }
    except Exception as e:
        return {'error': str(e)}

print(get_file_metadata("D:\home\image.jpg"))