# %%
from label_analysis.helpers import get_labels
import pandas as pd
import ipdb
from xnat.object_oriented import Proj, upload_nii_nodesc

from fran.utils.fileio import maybe_makedirs
tr = ipdb.set_trace

from pathlib import  Path
import SimpleITK as sitk
from pydicom import dcmread
from pylidc.utils import consensus
import matplotlib.pyplot as plt
import numpy as np

import pylidc as pl

from fran.utils.imageviewers import ImageMaskViewer

class LIDCProcessor():
    def __init__(self) -> None:
        
        self.proj_title = "lidc2"
        self.proj = Proj("lidc2")
        self.scans = pl.query(pl.Scan).filter()
        print(self.scans.count())
        self.imgs_fldr = Path("/home/ub/tmp/images")
        self.lm_fldr = Path("/home/ub/tmp/masks")

    def process_scan(self,scan,clevel=.35):
        case_id = self.get_case_id(scan)
        fn = "{0}_{1}.nii.gz".format(self.proj_title,case_id)
        fn_img = self.imgs_fldr/fn
        fn_lm = self.lm_fldr/fn
        if all([fn.exists() for fn in [fn_img,fn_lm]]):
            print("IMAGE and LM already in tmp folder")
        else:
            vol = scan.to_volume()
            lm_np= np.zeros_like(vol)
            lm_np = self.fill_lm(scan,lm_np,clevel)
            img, lm = self.scan_lm_to_nii(scan.spacings,vol,lm_np)

            sitk.WriteImage(img,fn_img)
            sitk.WriteImage(lm,fn_lm)
        self.maybe_upload_scan_rscs(scan,fn_img,fn_lm)



    def get_case_id(self,scan):
        case_id = scan.patient_id
        case_id = case_id.split("-")[-1]
        return case_id

    def fill_lm(self,scan,lm_np, clevel = .35):
        #clevel of 0.5 means if 1/2 ppl agree that voxel belong, it is labelled. lower threshold gives more liberal bounds
        nods = scan.cluster_annotations()
        for anns in nods :
            cmask,cbbox,lm_nps = consensus(anns, clevel=clevel) # liberal roi
                                          #pad=[(20,20), (20,20), (0,0)])

            cmask_int = np.zeros(cmask.shape)

            classes = [ann.malignancy for ann in anns]
            class_  =int(np.round(np.average(classes)))
            cmask_int[cmask]= class_

            lm_np[cbbox] = cmask_int
        return lm_np

    def scan_lm_to_nii(self,spacings, vol,lm_np):
        shape = vol.shape
        if shape[0]==shape[1]==512:
            vol2 = vol.transpose(2,0,1)
            lm_np2 = lm_np.transpose(2,0,1)

        else:
            tr()
        img = sitk.GetImageFromArray(vol2)
        img.SetSpacing(spacings)

        lm = sitk.GetImageFromArray(lm_np2)
        lm.SetSpacing(spacings)
        return img,lm

    def maybe_create_subject(self,scan):
        case_id = self.get_case_id(scan)
        subj = self.proj.subject(case_id)
        if not subj.exists():
            print("Creating subject {0}".format(case_id))
            subj.create()
        else:
            print("Using existing subject {0}".format(case_id))
        return subj

    def maybe_upload_scan_rscs(self,scan, fn_img,fn_lm):
        subj = self.maybe_create_subject(scan)
        case_id = self.get_case_id(scan)
        exp = subj.experiment("ct_{}".format(case_id))
        if not exp.exists():
            exp.create(experiments = 'xnat:ctSessionData')

        print("Creating IMAGE and LM_GT resources for {0}".format(scan.patient_id))
        self.maybe_upload_rsc(exp,"IMAGE",fn_img)
        self.maybe_upload_rsc(exp,"LM_GT",fn_lm)
        print("done")

    def maybe_upload_rsc(self,exp,label,fpath):

        rsc = exp.resource(label)
        if not rsc.exists():
            print("Uploading {0} as resource label {1}".format(fpath, label))
            rsc.file(fpath.name).put(fpath)
        else:
            print("File already in resource {0}".format(label))

        # upload_nii_nodesc(fname_out.name,label="NIFTI")

# %%
if __name__ == "__main__":
    L = LIDCProcessor()
    for indx in range(200):
        scn = L.scans[indx]

        L.process_scan(scn)
# %%
    scn = L.scans[0]
    sid = "0028"
    sids = [s for s in L.scans if sid in s.patient_id][0]


    case_id = L.get_case_id(scn)

    im,lm = L.process_scan(scn)

    proj_title = 'lidc2'
    proj = Proj(proj_title)

    fn_img = Path("/home/ub/tmp/images/{0}_{1}.nii.gz".format(proj_title,case_id))
    fn_lm = Path("/home/ub/tmp/masks/{0}_{1}.nii.gz".format(proj_title,case_id))

    maybe_makedirs("/home/ub/tmp/images")
    maybe_makedirs("/home/ub/tmp/masks")
    sitk.WriteImage(im,fn_img)
    sitk.WriteImage(lm,fn_lm)

    subj = proj.subject(case_id)
    subj.create()

    subj.experiment("ct").create(experiments = 'xnat:ctSessionData')
    exps =  subj.experiments()

    rsc = exp.resource("IMAGE").file(fn_img.name).put(fn_img)
    rsc = exp.resource("LM_GT").file(fn_lm.name).put(fn_lm)


    subj.experiments()[0]
# %%
    case_id = L.get_case_id(scn)
    fn = "{0}_{1}.nii.gz".format(L.proj_title,case_id)
    fn_img = L.imgs_fldr/fn
    fn_lm = L.lm_fldr/fn
    if all([fn.exists() for fn in [fn_img,fn_lm]]):
        print("IMAGE and LM already in tmp folder")
    else:
        vol = scn.to_volume()
        lm_np= np.zeros_like(vol)
        lm_np = L.fill_lm(scn,lm_np,clevel=.35)
        img, lm = L.scan_lm_to_nii(scn.spacings,vol,lm_np)

        sitk.WriteImage(im,fn_img)
        sitk.WriteImage(lm,fn_lm)

# %%
        subj = L.maybe_create_subject(scan)
        exp = subj.experiment("ct_{0}".format())
        if not exp.exists():
            exp.create(experiments = 'xnat:ctSessionData')


# %%

        case_id = L.get_case_id(scan)
        fn = "{0}_{1}.nii.gz".format(L.proj_title,case_id)
        fn_img = L.imgs_fldr/fn
        fn_lm = L.lm_fldr/fn
        if all([fn.exists() for fn in [fn_img,fn_lm]]):
            print("IMAGE and LM already in tmp folder")
        else:
            vol = scan.to_volume()
            lm_np= np.zeros_like(vol)
            lm_np = L.fill_lm(scan,lm_np,clevel)
            img, lm = L.scan_lm_to_nii(scan.spacings,vol,lm_np)


# %%
            scan =sids
            vol = scan.to_volume()
            lm_np= np.zeros_like(vol)
            lm_np = L.fill_lm(scan,lm_np,clevel=.34)
            img, lm = L.scan_lm_to_nii(scan.spacings,vol,lm_np)
            get_labels(lm)


# %%
