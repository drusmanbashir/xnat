# %%
import shutil
import time
from pathlib import Path
from tqdm import tqdm
from xnat.object_oriented import *
from dicom_utils.capestart_related import collate_nii_foldertree

from fran.utils.string import  int_to_str
from label_analysis.utils import fix_slicer_labelmap, get_metadata, thicken_nii
from xnat.object_oriented import *
from fran.utils.fileio import maybe_makedirs


# %%
if __name__ == "__main__":
    proj_title='lidc2'
    proj = Proj(proj_title)
    df= proj.create_report(mask_label="LM_GT",img_label ="IMAGE", search_level= "exps",add_label_info=True)
    proj.export_nii(symlink=True,overwrite=True,ensure_fg=True)
    subs = proj.subjects()

    csv_fn = "/tmp/img_mask_fpaths.csv"

    df = pd.read_csv(csv_fn)
    df.dropna(inplace=True)
    fldrs = proj.export_folder/"images", proj.export_folder/"masks"
    [maybe_makedirs(f) for f in fldrs]
    filesets=  df.img_fpaths, df.mask_fpaths

# %%
# %% [markdown]
## Download rscs with criteria
# %%
    sub_ids = [Subj(sub).get_pt_id(False) for sub in subs]
    dest_fldr = "/s/tmp"
# %%
# %%

    fldr = Path("/s/xnat_shadow/lidctmp")
    fldr1 = fldr/("images")
    fldr2 = fldr/("masks")
    maybe_makedirs([fldr1,fldr2])
# %%
    for sub in subs[:5]:
        sub = Subj(sub)
        sub.download_rscs("IMAGE",fldr1)
        sub.download_rscs("LM_GT",fldr2)
# %%
    collate_nii_foldertree(fldr2,fldr2)
    collate_nii_foldertree(fldr1,fldr1)
# %%
    # if any(r.label()=='LABEL_GT' for r in rscs):
    #     sub.download_rscs("LABEL_GT","/s/xnat_shadow/crc/test/labels/")
# %%

# %% [markdown]
## XML retrievals
# %%
    from dicom_utils.metadata import *
    cols = 'case_id','filename', 'date', 'vendor','model','kernel','filter_type','kvp','current' , 'exposure_time','exposure','ctdi','thickness'
    tag_list =vendor,model ,kernel,filter_type,kvp,current,exposure_time, exposure,ctdi,thickness
# %%
    all_exps=[]
    for i in tqdm(range(len(subs))):
        sub= subs[i]
        case_id = sub.get_pt_id()
        for j in range(len(sub.exps)):
            dat = []
            exp= sub.exps[j]
            date=exp.date
            x=exp.x
            fn= x.get_uri('IMAGE')
            fn= fn.name
            dcm_fns = x.get_uri("DICOM")
            hdr = dcmread(dcm_fns[0])
            vals= [case_id,fn , date]
            for tg in tag_list:
                try:
                    val = hdr[tg].value 
                except:
                    val= None
                vals.append(val)
            dat+= vals
            all_exps.append(dat)

# %%

    df = pd.DataFrame(data=all_exps,columns = cols)
    df.to_csv("/s/xnat_shadow/crc/dcm_summary.csv",index=False)
# %%

    def factorial(n):
        if n == 0:

            



# %% [markdown]
## Upload MASKS
# %%



    fldr = Path("/s/datasets_bkp/crc_project/nifti/masks_ub/finalised/")
    fpath = Path("/s/xnat_shadow/crc/wxh/masks_manual_final/crc_CRC326_20140110_ABDOMEN.nrrd")
# %%

    for fpath in fldr.glob("*"):
        if fpath.is_file():
            upload_nii(fpath,label="LABEL_GT",xnat_tags=['manual'])


# %% [markdown]
## Fix masks
        





# %%
    
        
# %%
    mask_label = "MASK_THICK"
    img_label = mask_label.replace("MASK","IMAGE")
    csv_label ="IMAGE_MASK_FPATHS"
    ss = proj.get_subs_with_rsc(mask_label)
    img_fpaths,mask_fpaths=[],[]
    for s in ss:
            scns = [scn for scn in s.scans if scn.has_rsc(mask_label)]
            for sc in scns:
                mask_fpaths.append(sc.get_rsc_fpaths(mask_label)[0])
                img_fpaths.append(sc.get_rsc_fpaths(img_label)[0])
    tmp = list(zip(img_fpaths,mask_fpaths))
    df = pd.DataFrame(tmp, columns = ["img_fpaths","mask_fpaths"])
    csv_fn = Path("/tmp/img_mask_fpaths.csv")
    df.to_csv(csv_fn,index=False)
    proj.add_rsc(csv_fn,label=csv_label,content="CSV",format="CSV",force=True)

# %%
# %% [markdown]
## Download all nifti masks and images
# %% 
    df = proj.create_report("MASK_THICK")
    proj.export_nii(symlink=False,overwrite=True)
    for i in range(len(df)):
        row = df.iloc[i]
        mask_fn = Path(row.mask_fpaths)
        img_fn = Path(row.img_fpaths)
        fix_slicer_labelmap(mask_fn,img_fn)

# %%

# %% [markdown]
## Delete unwanted subjects
    bad_ids = [61,63,64,65,66,67,68,'n14','n15','n16','nn1']
    for id in bad_ids:
        sub = proj.subject(str(id))
        print(sub)
        sub.delete()
        

# %%

# %% [markdown]
##  Convert DICOM / DCM2NII
# %%
    proj_title = 'lidc'
    keep_desc = True
# %%
    proj = Proj(proj_title)
    subs = proj.subs
# %%
    j=0
    for i in range(j,len(subs)):
        ss = subs[i]
        for scn in ss.scans:
            scn.dcm2nii(desc_in_fname=keep_desc)

        print(i)
        j=i

# %%
    dest_fldr="/s/insync/datasets/crc_project/images_ko/"
    ss.download_rscs("IMAGE",dest_fldr)
# %% [markdown]
## Moving files downloaded from xnat to single folder
# %%

    fldr = Path("/home/ub/Downloads/scans")
    collate_nii_foldertree(fldr)
   
# %%
# %% [markdown]
## Thicken images
# %%
    proj_title="nodes"
    proj=Proj(proj_title)
    orphan_thick_masks=[]

    subs = proj.subs
# %%
    for n in range(len(subs)):
        sub = subs[n]
        scns = sub.scans
        for scn in scns:
            rscs = scn.resources()
            labels = [r.label() for r in rscs]
            if "MASK_THICK" in labels and not "IMAGE_THICK" in labels:
            # rsc = rscs[0]
                mask_fn = scn.get_rsc_fpaths("MASK_THICK")[0]
                mask = sitk.ReadImage(mask_fn)
                meta = get_metadata(mask)
                thickness = meta[2][2]
                nslices = meta[0][2]
                img_fn= scn.get_rsc_fpaths("IMAGE")[0]

                img = sitk.ReadImage(img_fn)
                out_fname =  Path(mask_fn).name
                out_fname= out_fname.replace(".gz.gz",".gz")
                out_fullpath = Path("/tmp")/out_fname
                img = thicken_nii(img_fn,thickness)
                img_nslices = img.GetSize()[-1]
                meta2 = get_metadata(img)
                sitk.WriteImage(img,out_fullpath)

                if not img.GetSize()[-1]==nslices:
                    tr()
                else:
                    scn.add_rsc(fpath=out_fullpath,label="IMAGE_THICK")

# %%



# %%
# %% [markdown]
## Fix slicer labelmaps
# %%
    target_label="IMAGE_THICK"
    msks = list(Path("/home/ub/Desktop/capestart/liver/masks").glob("*"))
    for msk in msks:
        m= sitk.ReadImage(msk)
        print("{0}.... {1}".format(msk,m.GetSize()))
        img = get_matching_rsc(msk)
        fix_slicer_labelmap(msk,img)
# %%
# %% [markdown]
## Move downloaded files into a single folder
# %%

    imgs_fldr = "/s/xnat_shadow/crc/test/labels/"
    dest = Path(imgs_fldr)/"tmp"
    collate_nii_foldertree(imgs_fldr,dest,fname_cond="")
# %%

##  Delete all NIFTI and IMAGES
# %%
    proj_title = 'nodes'
    p = Proj(proj_title)
    p.delete_rscs("MASK_THICK")

# %% [markdown]
## Filter resources
# %%
    c,_ = login()

    c.inspect.datatypes('xnat:projectData')

# %%
    constraints = [
                  ('xnat:subjectData/PROJECT', '=', 'nodes'),
                   'OR',

                   [('xnat:subjectData/AGE','>','14'),

                    'AND'

                    ]

                   ]
# %%
    aa=    c.select('xnat:subjectData',
             [
             'xnat:subjectData/SUBJECT_ID'
             ]
                    ).where(constraints)
# %%
    aa =c.select('xnat:subjectData',

               ['xnat:subjectData/SUBJECT_ID',

                'xnat:subjectData/AGE']

        ).where(constraints)
# %%
