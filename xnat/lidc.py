# %%
import matplotlib.pyplot as plt
import numpy as np

import pylidc as pl

from fran.utils.imageviewers import ImageMaskViewer
scans = pl.query(pl.Scan).filter(pl.Scan.slice_thickness <= 1,
                                 pl.Scan.pixel_spacing <= 0.6)
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

print(contours[1])
print(mask.shape, mask.dtype)
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
ImageMaskViewer([vol,m2])

fig,ax = plt.subplots(1,2,figsize=(5,3))

ax[0].imshow(vol[bbox][:,:,2], cmap=plt.cm.gray)
ax[0].axis('off')

ax[1].imshow(mask[:,:,2], cmap=plt.cm.gray)
ax[1].axis('off')

plt.tight_layout()
#plt.savefig("../images/mask_bbox.png", bbox_inches="tight")
plt.show()
# %%
