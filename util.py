import json
import numpy as np
import h5py
import xml.etree.ElementTree as ET
import hyperspy.api as hs
from igor2 import binarywave  # For handling .ibw files from igor2 package


# JSON Encoder for numpy types and complex numbers
class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, bytes):
            return obj.decode("utf-8")  # Decode bytes as utf-8 string
        elif isinstance(obj, complex):  # Handle Python's built-in complex type
            return [obj.real, obj.imag]
        else:
            return super(MyEncoder, self).default(obj)


# Function to read .h5 (HDF5) files with the length check
def read_h5_file(file_name):
    def extract_h5_data(name, obj):
        # Only include attributes where the length of the value is <= 10
        attrs = {k: v for k, v in obj.attrs.items() if len(str(v)) <= 10}
        return {name: attrs}

    with h5py.File(file_name, 'r') as f:
        metadata = {}
        f.visititems(lambda name, obj: metadata.update(extract_h5_data(name, obj)))
    return metadata


# Function to read .xrdml (XRDML) files with the length check
def read_xrdml_file(file_name):
    tree = ET.parse(file_name)
    root = tree.getroot()

    # Extract metadata from XML structure, skipping elements with value length > 10
    metadata = {}
    for elem in root.iter():
        if elem.text and len(elem.text) <= 10:
            metadata[elem.tag] = elem.text
    return metadata


# Function to read .dm4 (DigitalMicrograph) files with the length check
def read_dm4_file(file_name):
    s = hs.load(file_name)  # Load the .dm4 file using HyperSpy
    metadata = s.metadata.as_dictionary()  # Extract metadata as a dictionary

    # Filter out metadata entries with value lengths > 10
    filtered_metadata = {k: v for k, v in metadata.items() if len(str(v)) <= 10}
    return filtered_metadata


# Function to read .ibw (Igor Binary Wave) files with the length check
def _read_parms(wave):
    """
    Extract metadata (parameters) from the wave, skipping values longer than 10 characters.
    """
    parm_dict = {}
    parm_string = wave['note']
    if isinstance(parm_string, bytes):
        try:
            parm_string = parm_string.decode("utf-8")
        except UnicodeDecodeError:
            parm_string = parm_string.decode("ISO-8859-1")  # Fallback for older encoding

    parm_string = parm_string.rstrip("\r").replace(".", "_")
    parm_list = parm_string.split("\r")

    for pair_string in parm_list:
        temp = pair_string.split(":")
        if len(temp) == 2:
            temp = [item.strip() for item in temp]
            try:
                num = float(temp[1])

                # Check if the number is infinity and skip it
                if np.isinf(num):
                    continue

                # Skip values with length > 10
                if len(str(num)) <= 10:
                    parm_dict[temp[0]] = int(num) if num == int(num) else num
            except ValueError:
                if len(temp[1]) <= 10:
                    parm_dict[temp[0]] = temp[1]

    return parm_dict


def read_ibw_file(file_name):
    """
    Function to read .ibw (Igor Binary Wave) files with the length check.
    """
    with open(file_name, "rb") as f:
        ibw_obj = binarywave.load(f)  # Load the .ibw file using igor2

    wave = ibw_obj['wave']  # Extract wave data

    # Extract parameters from the wave
    metadata = _read_parms(wave)
    return metadata


# Unified function to handle different file types
def get_metadata(file_name):
    if file_name.endswith('.h5'):
        return read_h5_file(file_name)
    elif file_name.endswith('.xrdml'):
        return read_xrdml_file(file_name)
    elif file_name.endswith('.dm4'):
        return read_dm4_file(file_name)
    elif file_name.endswith('.ibw'):
        return read_ibw_file(file_name)
    else:
        raise ValueError("Unsupported file format")