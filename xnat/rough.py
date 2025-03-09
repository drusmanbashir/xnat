# %%
import os

import pandas as pd
from pydicom.filereader import read_dicomdir
import itertools as il
import SimpleITK as sitk
import ipdb
from pydicom import dcmread
from pyxnat.core.resources import shutil

from utilz.imageviewers import view_sitk
from utilz.string import strip_extension
tr = ipdb.set_trace

from pathlib import Path
from bs4 import BeautifulSoup as BS
from pyxnat import Interface

from utilz.helpers import dec_to_str, find_matching_fn, pp
central = Interface(server='http://localhost:8080/xnat-web-1.8.8', user='admin', password='admin')
subject_id = 'your_subject_id'
from utilz.fileio import load_file, load_xml
custom_tags = ['tag1', 'tag2', 'tag3']
# %%

if __name__ == "__main__":
    fldr = Path("/s/xnat_shadow/nodes/capestart/completed/lms/")
    fns  = list(fldr.glob("*.*"))
    df = pd.read_csv("/s/xnat_shadow/nodes/capestart_pseudoids.csv")
    for fn in fns:
        # name = "capestart/case_166.nii.gz"
        name = fn.name
        fn_org = df[df.fn_out.str.contains(name)]['fn_org'].item()
        fn_org = Path(fn_org)
        name_org = fn_org.name
        fn_out= fn.parent/name_org
        shutil.move(fn,fn_out)


# %%
    fldr_lm = Path("/s/xnat_shadow/nodes/nodes_thin/lms")
    fns  = list(fldr_lm.glob("*.*"))

    for fn in fns:
        fldr_out = Path("/s/xnat_shadow/nodes/nodes_thin/images")
        fldr_imgs= Path("/s/xnat_shadow/nodes/images_pending")
        fns_imgs = list(fldr_imgs.glob("*.*"))

        fn_img = find_matching_fn(fn,fns_imgs)
        fn_out = fldr_out/fn_img.name
        shutil.move(fn_img,fn_out)
# %%

    row = df.iloc[0]
    fn_org = row.fn_org



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


