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
from utilz.string import info_from_filename, strip_extension
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

    fldr3 ="/r/tmp/nodes" 
    fn_all = list(Path(fldr3).glob("*"))


    imgs= Path("/s/xnat_shadow/nodes/images")
    imgs_pending = Path("/s/xnat_shadow/nodes/images_pending")

    fns_pending = list(imgs_pending.glob("*"))
    fns = list(imgs.glob("*"))
    fns_all = fns_pending+fns

    cids_done = [info_from_filename(fn.name)['case_id'] for fn in fns_all]
    cids_done = set(cids_done)
    print(len(cids_done))
    
    # Filter out files from fn_all that have CIDs matching those in cids_done
# %%
    fn_all_filtered = []
    dones=[]
    for fn in fn_all:
        cid = info_from_filename(fn.name)['case_id']
        if cid not in cids_done:
            fn_all_filtered.append(fn)
        else:
            dones.append(cid)
    dones_confirmed = set(dones)
    print(len(dones_confirmed))    
    # Replace the original fn_all with the filtered version
    # fn_all = fn_all_filtered

# %%
    for fn in fn_all_filtered:
        shutil.move(fn,imgs_pending)

    # Filter files in imgs_pending that have "neck" (case insensitive) in their names
# %%
    import re
    
    neck_pattern = re.compile(r'neck', re.IGNORECASE)
    neck_files = [fn for fn in list(imgs_pending.glob("*")) if neck_pattern.search(fn.name)]
    
    # Create a copy of neck_files for later reference
    neck_files_info = [fn.name for fn in neck_files]
    
    # Create the destination directory if it doesn't exist
    fldr_necks = Path("/s/xnat_shadow/nodes/images_pending_necks")
    if not fldr_necks.exists():
        fldr_necks.mkdir(parents=True, exist_ok=True)
    
    # Move the files
    for fn in neck_files:
        try:
            shutil.move(str(fn), str(fldr_necks))
            print(f"Moved {fn.name} to {fldr_necks}")
        except Exception as e:
            print(f"Error moving {fn.name}: {e}")
    
# %%
    print(f"Found {len(neck_files_info)} files with 'neck' in their names:")

# %%
    for name in neck_files_info:
        print(f"  - {name}")
    
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


