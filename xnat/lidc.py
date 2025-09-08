#
import numpy as np
import configparser
img_fns = list(dest_fldr.rglob("IMAGE/*.nii.gz"))

# NumPy 2.0+: restore deprecated aliases used by pylidc
if not hasattr(np, "int"):    np.int = int
if not hasattr(np, "float"):  np.float = float
if not hasattr(np, "bool"):   np.bool = bool
if not hasattr(np, "object"): np.object = object

# Python 3.12+: restore SafeConfigParser alias used by pylidc
if not hasattr(configparser, "SafeConfigParser"):
    configparser.SafeConfigParser = configparser.ConfigParser

import pylidc as pl 
import ipdb
from xnat.object_oriented import Proj

from utilz.fileio import maybe_makedirs
tr = ipdb.set_trace

from pathlib import  Path
import SimpleITK as sitk
from pylidc.utils import consensus
import numpy as np

import pylidc as pl


class LIDCProcessor():
    """Processes LIDC-IDRI dataset scans and uploads them to XNAT."""
    
    def __init__(self) -> None:
        self.proj_title = "lidc"
        self.proj = Proj("lidc")
        self.scans = pl.query(pl.Scan).filter()
        print(self.scans.count())
        self.imgs_fldr = Path("/s/tmp/images")
        self.lm_fldr = Path("/s/tmp/masks")
        maybe_makedirs([self.imgs_fldr,self.lm_fldr])
        

    def process_scan(self,scan,clevel=.35):
        """Process a single LIDC scan and upload to XNAT if not already present."""
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
        """Extract case ID from scan patient ID."""
        case_id = scan.patient_id
        case_id = case_id.split("-")[-1]
        return case_id

    def fill_lm(self,scan,lm_np, clevel = .35):
        """Fill landmark mask with consensus annotations from radiologists."""
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
        """Convert scan volume and landmark mask to NIfTI format."""
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
        """Create XNAT subject if it doesn't exist, otherwise return existing subject."""
        case_id = self.get_case_id(scan)
        subj = self.proj.subject(case_id)
        if not subj.exists():
            print("Creating subject {0}".format(case_id))
            subj.create()
        else:
            print("Using existing subject {0}".format(case_id))
        return subj

    def maybe_upload_scan_rscs(self,scan, fn_img,fn_lm):
        """Upload scan image and landmark resources to XNAT experiment."""
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
        """Upload a file as a resource to XNAT experiment if it doesn't already exist."""

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
    # indx=0
    for indx in range(351,400):
        scn = L.scans[indx]
        L.process_scan(scn)
# %%

# %%
#SECTION:-------------------- COLLATE DONLOADED NII FILES FROM XNAT--------------------------------------------------------------------------------------

src_fldr = Path("/media/UB/admin-20250908_021922")
dest_fldr = Path("/media/UB/datasets/lidc")
maybe_makedirs(dest_fldr)
maybe_makedirs(dest_fldr/("images"))
maybe_makedirs(dest_fldr/("lms"))
img_fldr = dest_fldr/("images")
lms_fldr = dest_fldr/("lms")

# %%
img_fns = list(src_fldr.rglob("*IMAGE*/*.nii.gz"))
lm_fns =list(src_fldr.rglob("*LM*/*.nii.gz"))
# %%
desti_fldr = lms_fldr
for fn in lm_fns:
    fn_neo =desti_fldr/fn.name
    print("{0}   ---->   {1}".format(fn,fn_neo))
    shutil.move(fn,fn_neo)
# %%
desti_fldr = img_fldr
for fn in img_fns:
    fn_neo =desti_fldr/fn.name
    print("{0}   ---->   {1}".format(fn,fn_neo))
    shutil.move(fn,fn_neo)
# %%
