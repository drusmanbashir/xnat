# %%
import pandas as pd
import ipdb
from xnat.object_oriented import upload_nii_nodesc
tr = ipdb.set_trace

from pathlib import  Path
import SimpleITK as sitk
from pydicom import dcmread
from pylidc.utils import consensus
import matplotlib.pyplot as plt
import numpy as np

import pylidc as pl

from fran.utils.imageviewers import ImageMaskViewer
scans = pl.query(pl.Scan).filter(pl.Scan.slice_thickness <= 1,
                                 pl.Scan.pixel_spacing <= 0.6)
scans = pl.query(pl.Scan).filter()
print(scans.count())
# => 31

pid = 'LIDC-IDRI-0078'
scan = pl.query(pl.Scan).filter(pl.Scan.patient_id == pid).first()
# %%

ann = pl.query(pl.Annotation).first()
q = pl.query(pl.Annotation)
f = q.first()
iteri = iter(q)
aa = next(iteri)
print(ann.scan.patient_id)
contours = ann.contours
# %%

print(contours[1])
# %%
vol = ann.scan.to_volume()

padding = [(30,10), (10,25), (0,0)]

m2 = np.zeros_like(vol)
# %%
for ann in iter(q):
    bbox = ann.bbox_matrix()
    sides = bbox[:,1]-bbox[:,0]
    mask = ann.boolean_mask(bbox = bbox)
    try:
        m2[bbox[0][0]:bbox[0][1],bbox[1][0]:bbox[1][1],bbox[2][0]:bbox[2][1]] = mask
    except:
        pass

# %%
# %%
dics = []
for idx, scan in enumerate(scans):
    scan = scans[0]

class LIDCProcessor():
    def __init__(self) -> None:
        
        self.scans = pl.query(pl.Scan).filter()
        print(self.scans.count())
    def process_scan(self,scan,clevel=.35):
        vol = scan.to_volume()
        lm_np= np.zeros_like(vol)
        lm_np = self.fill_lm(scan,lm_np,clevel)
        img, lm = self.scan_lm_to_nii(scan.spacings,vol,lm_np)

        return img,lm


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


        # upload_nii_nodesc(fname_out.name,label="NIFTI")

if __name__ == "__main__":
    L = LIDCProcessor()
    scn = L.scans[0]
    im,lm = L.process_scan(scn)
    sitk.WriteImage(im, 'im.nii.gz')
    sitk.WriteImage(lm, 'lm.nii.gz')

df = pd.DataFrame(dics)
df.to_csv("lidc_headers_info.csv", index=False)
# %%


# Query for a scan, and convert it to an array volume.

mask= np.zeros_like(vol)
nods = scan.cluster_annotations()
# %%
for anns in nods :

# Perform a consensus consolidation and 50% agreement level.
# We pad the slices to add context for viewing.
    cmask,cbbox,masks = consensus(anns, clevel=0.35,) # liberal roi
                                  #pad=[(20,20), (20,20), (0,0)])

    cmask_int = np.zeros(cmask.shape)

    classes = [ann.malignancy for ann in anns]
    class_  =int(np.round(np.average(classes)))
    cmask_int[cmask]= class_

    mask[cbbox] = cmask_int


# %%
vol2 = vol.transpose(2,0,1)

img = sitk.GetImageFromArray(vol2)
img.SetSpacing(scan.spacings)
sitk.WriteImage(img, 'vol.nii.gz')
# %%

ann = anns[0]
# %%
ImageMaskViewer([vol,mask])
# %%
fig,ax = plt.subplots(1,2,figsize=(5,3))

ax[0].imshow(vol[bbox][:,:,2], cmap=plt.cm.gray)
ax[0].axis('off')

ax[1].imshow(mask[:,:,2], cmap=plt.cm.gray)
ax[1].axis('off')

plt.tight_layout()
#plt.savefig("../images/mask_bbox.png", bbox_inches="tight")
plt.show()
# %%
