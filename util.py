from igor import binarywave as bw
import json
import numpy as np


def _read_parms(ibw_wave, codec='utf-8'):
        
        parm_string = ibw_wave.get('note')
        if type(parm_string) == bytes:
            try:
                parm_string = parm_string.decode(codec)
            except:
                parm_string = parm_string.decode('ISO-8859-1')  # for older AR software
        parm_string = parm_string.rstrip('\r')
        parm_string = parm_string.replace(".","_")
        parm_list = parm_string.split('\r')
        parm_dict = dict()
        for pair_string in parm_list:
            temp = pair_string.split(':')
            if len(temp) == 2:
                temp = [item.strip() for item in temp]
                try:
                    num = float(temp[1])
                    parm_dict[temp[0]] = num
                    try:
                        if num == int(num):
                            parm_dict[temp[0]] = int(num)
                    except OverflowError:
                        pass
                except ValueError:
                    parm_dict[temp[0]] = temp[1]

        # Grab the creation and modification times:
        other_parms = ibw_wave.get('wave_header')
        for key in ['creationDate', 'modDate', 'bname']:
            try:
                parm_dict[key] = other_parms[key]
            except KeyError:
                pass
        return parm_dict



    
def _get_chan_labels(ibw_wave, codec='utf-8'):
        
        temp = ibw_wave.get('labels')
        labels = []
        for item in temp:
            if len(item) > 0:
                labels += item
        for item in labels:
            if item == '':
                labels.remove(item)

        default_units = list()
        for chan_ind, chan in enumerate(labels):
            # clean up channel names
            if type(chan) == bytes:
                chan = chan.decode(codec)
            if chan.lower().rfind('trace') > 0:
                labels[chan_ind] = chan[:chan.lower().rfind('trace') + 5]
            else:
                labels[chan_ind] = chan
            # Figure out (default) units
            if chan.startswith('Phase'):
                default_units.append('deg')
            elif chan.startswith('Current'):
                default_units.append('A')
            else:
                default_units.append('m')

        return labels, default_units
    
    
def _parse_file_path(self, input_path):
        pass

def _read_data(self):
        pass


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, bytes):
            return str(obj)
        else:
            return super(MyEncoder, self).default(obj)
        
        
def get_metadata(file_name):
        
        ibw_obj = bw.load(file_name)
        parm_encoding='utf-8'

        ibw_wave = ibw_obj.get('wave')
        parm_dict = _read_parms(ibw_wave, parm_encoding)
        chan_labels, chan_units = _get_chan_labels(ibw_wave, parm_encoding)
        
        #Main data
        # images = ibw_wave.get('wData')

        #JSON serialize metadata
        metadata = json.dumps(parm_dict, cls=MyEncoder)
        metadata = json.loads(metadata)
        #metadata.update({"File_path" : file_path})

        return metadata