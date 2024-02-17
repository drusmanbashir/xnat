# %%
import os
import pandas as pd
from pydicom.filereader import read_dicomdir
import itertools as il
import SimpleITK as sitk
import ipdb
from pydicom import dcmread
from pyxnat.core.resources import shutil

from fran.utils.imageviewers import view_sitk
tr = ipdb.set_trace

from pathlib import Path
from bs4 import BeautifulSoup as BS
from pyxnat import Interface

from fran.utils.helpers import dec_to_str, pp
central = Interface(server='http://localhost:8080/xnat-web-1.8.8', user='admin', password='admin')
subject_id = 'your_subject_id'
custom_tags = ['tag1', 'tag2', 'tag3']
from fran.utils.fileio import load_file, load_xml

if __name__ == "__main__":
    fldr = Path("/s/xnat_shadow/litq/test/images/")
    fls = list(fldr.rglob("*"))
    fls = [f for f in fls if f.is_file()]

    fl = fls[0]
# %%
    for fl in fls:
        if fl.parent!=fldr:
            print(fl)
            shutil.move(fl,fldr)
# %%


