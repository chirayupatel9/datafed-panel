from materials.AFM.bandexcitation.h5 import H5
from materials.AFM.oxfordAFM.ibw import IBW
from materials.EM.dm.dm4 import DM4
from materials.Xray.panalytical.xrdml import XRDML


def get_metadata(file_name):
    if file_name.endswith('.h5'):
        return H5(file_name).extract()
    elif file_name.endswith('.xrdml'):
        return XRDML(file_name).extract()
    elif file_name.endswith('.dm4'):
        return DM4(file_name).extract()
    elif file_name.endswith('.ibw'):
        return IBW(file_name).extract()
    else:
        raise ValueError("Unsupported file format")