# %%
import shutil
import time
from pathlib import Path
from tqdm import tqdm
from utilz.helpers import set_autoreload
from xnat.object_oriented import *
from xnat.helpers import collate_nii_foldertree

from dicom_utils.helpers import dcm_segmentation
from xnat.object_oriented import Subj
from pathlib import Path
import os
from label_analysis.utils import fix_slicer_labelmap, get_metadata, thicken_nii
from xnat.object_oriented import *
from utilz.fileio import maybe_makedirs


# %%
if __name__ == "__main__":
    set_autoreload()
    proj_title='tcgalihc'
    proj_title='tciaclm'
    proj_title='lidc'
    proj_title='bones'
    proj_title='litq'
    proj = Proj(proj_title)
# %%
    subs = [139, 141, 142]
    proj.dcm2nii(add_date=True,add_desc=True,overwrite=False, subs=subs)
# %%
    proj.dcm2nii(add_date=True,add_desc=True,overwrite=True)

# %%

    subs_to_do = []
    for sub in proj.subs:
            subs_to_do.append(sub)

# %%
# %%
    proj.collate_metadata()
# %%
    import pwd
    pw = pwd.getpwnam('xnat')
    uid = pw.pw_uid
    os.setuid(uid)
    # df= proj.create_report()
# %%


# ---- Config ----
    pt_id = "nodes_110"               # Your subject ID (without project prefix)
    project = "nodes"              # Your project name
    scan_index = 0                 # Or choose scan ID directly
    label = "IMAGE"                # Resource label
    dest = Path("/tmp/xnat_manual")  # Local download path
    dest.mkdir(parents=True, exist_ok=True)

# ---- Load subject and scan ----
    sub = Subj.from_pt_id('110','nodes')
    scan = sub.scans[scan_index]  # or sub.scans[scan_id] if you know it

    rscs = scan.esp.resources()
    print(list(rscs))
# ---- Download resource ----
    rsc = next((r for r in scan.esp.resources() if r.label() == label), None)
    if not rsc:
        print(f"No resource labeled {label} found.")
    else:
        print(f"Downloading {label} to {dest}...")
        rsc.get(dest, extract=True)
        print("Done.")
    # proj.export_nii(symlink=True,overwrite=True,ensure_fg=True,label=label)
# %%
    subs = proj.subjects()
    csv_fn = "/tmp/img_mask_fpaths.csv"

    df = pd.read_csv(csv_fn)
    df.dropna(inplace=True)
    fldrs = proj.export_folder/"images",
    # proj.export_folder/"masks"+    [maybe_makedirs(f) for f in fldrs]
    filesets=  df.img_fpaths, df.mask_fpaths

# %%
# %% [markdown]
## Download rscs with criteria
# %%
    sub_ids = [Subj(sub).get_pt_id(False) for sub in subs]
    dest_fldr = "/s/tmp"
# %%
# %%

    fldr = Path("/s/xnat_shadow/nodes/images_more/")
    fldr1 = fldr/("images")
    fldr2 = fldr/("masks")
    maybe_makedirs([fldr1,fldr2])
# %%
    ids_list =["crc_CRC"+str(num) for num in range(375,400)]
    for sub in subs:
        sub = Subj(sub)
        id_ = sub.get_pt_id()
        print(id_)
        if id_ in ids_list:
            print("Downloading")
            sub.download_rscs("IMAGE",fldr1)
        # sub.download_rscs("LM_GT",fldr2)
# %%
    fldr2 ="/r/tmp/notes" 
    fldr3 ="/r/tmp/nodes" 
    collate_nii_foldertree(fldr2,fldr3)
    collate_nii_foldertree(fldr1,fldr1)
# %%




    src_fldr = Path("/s/xnat_shadow/tcianodes/")
    ni = list(src_fldr.rglob("*"))
    img_fns = [fn for fn in ni if "IMAGE" in str(fn) and ".nii.gz" in fn.name]
    lm_fns = [fn for fn in ni if "LABELMAP" in str(fn) and ".nii.gz" in fn.name]
# %%
    dest_fldr = src_fldr/("lms")
    for fn in lm_fns:
            fn_neo =dest_fldr/fn.name
            print("{0}   ---->   {1}".format(fn,fn_neo))
            shutil.move(fn,fn_neo)


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
    subs = list(subs)
    for i in tqdm(range(len(subs))):
        sub= subs[i]
        sub = Subj(sub)
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

           



# %% [markdown]
# %%
#SECTION:-------------------- UPLOAD GT--------------------------------------------------------------------------------------
# %%


# %%

    fldr = Path("/s/datasets_bkp/litq/sitk/lms")
    for fpath in fldr.glob("*"):
        if fpath.is_file():
            upload_nii(fpath,has_desc=False,label="LABELMAP",xnat_tags=[])


# %% [markdown]
## Fix masks
        


# %%
    
        
# %%
    mask_label = "MASK_THICK"
    img_label = mask_label.replace("MASK","IMAGE")
    img_label = "IMAGE"
    csv_label ="IMAGE_MASK_FPATHS"
    ss = proj.get_subs_with_rsc(img_label)
    img_fpaths,mask_fpaths=[],[]
# %%
    for s in ss[:10]:
            scns = [scn for scn in s.scans if scn.has_rsc(img_label)]
            for sc in scns:
                mask_fpaths.append(sc.get_rsc_fpaths(mask_label)[0])
                img_fpaths.append(sc.get_rsc_fpaths(img_label)[0])
# %%
    tmp = list(zip(img_fpaths,mask_fpaths))
    df = pd.DataFrame(tmp, columns = ["img_fpaths","mask_fpaths"])
    csv_fn = Path("/tmp/img_mask_fpaths.csv")
    df.to_csv(csv_fn,index=False)
    # proj.add_rsc(csv_fn,label=csv_label,content="CSV",format="CSV",force=True)

# %%
# %% [markdown]
## Download all nifti masks and images
# %% 
    df = proj.create_report()
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
    for id_ in bad_ids:
        sub = proj.subject(str(id_))
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
    proj.dcm2nii()
    subs = proj.subs
    scn = sub.scans[0]
    scn.get_filesetXML()
    scn.dcm_fns

    if scn.datatype()=="xnat:segScanData":
        sc = ScnSeg(scn)

# %%
        add_date= False
        add_desc= False
        dcm_fn1= scn.dcm_fns[0]
        fldr = Path(dcm_fn1).parent
        nii_fname = scn.generate_nii_fname(dcm_fn1,add_date, add_desc)


        img= dcm_segmentation(dcm_fn1)



        reader = sitk.ImageSeriesReader()
        dcm_names = reader.GetGDCMSeriesFileNames(str(fldr))
        reader.SetFileNames(dcm_names)
        img = reader.Execute()
        tmp_nm= Path("/home/ub/.tmp/{0}".format(nii_fname))
        sitk.WriteImage(img,tmp_nm)
        scn.add_rsc(fpath = tmp_nm, label=label)

# %%
    j=0
    keep_desc=True
    for i,sub in enumerate(subs):
        sub = Subj(sub)
        for scn in sub.scans:
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

