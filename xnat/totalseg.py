# %%
import shutil
from itk import image
from label_analysis.helpers import get_labels, to_int, to_label
import functools as fl
import pandas as pd
import ipdb
from xnat.object_oriented import Proj, upload_nii_nodesc
from utilz.imageviewers import ImageMaskViewer, view_sitk

from utilz.fileio import maybe_makedirs
from utilz.helpers import chunks, find_matching_fn
from utilz.string import strip_extension
tr = ipdb.set_trace

from pathlib import  Path
import SimpleITK as sitk
from pydicom import dcmread
import matplotlib.pyplot as plt
import numpy as np


class TotalSegMerger():
    def __init__(self, parent_fldr, output_fldr,image_ids=None) -> None:
        self.parent_fldr = parent_fldr
        self.meta  = pd.read_excel(parent_fldr/("meta.xlsx"))
        if image_ids is not None:
            self.filter_meta(image_ids)
                             
        self.meta_labels = pd.read_excel(parent_fldr/("meta.xlsx"),sheet_name="labels")
        self.case_fldrs = list(self.parent_fldr.glob("*"))
        self.output_fldr = output_fldr
        self.imgs_fldr = output_fldr/("images")
        self.masks_fldr = output_fldr/("masks")
        self.load_output_df()

    def filter_meta(self,image_ids):
        self.meta = self.meta[self.meta.image_id.isin(image_ids)]
        self.meta.reset_index(inplace=True)

    def load_output_df(self):
        self.output_df_fn = self.parent_fldr/("output_df.csv")
        if not self.output_df_fn.exists():
            self.df_out = pd.DataFrame(self.meta.copy())
            self.df_out['unexpected']=0
            self.df_out.to_csv(self.output_df_fn,index=False)
        else:
            self.df_out = pd.read_csv(self.output_df_fn)

    def process_dataset(self,overwrite=False):
        for idx in range(len(self.meta)):
            res= self.process_idx(idx,overwrite=overwrite)
            self.df_out.loc[idx]=res[0]
            self.df_out.to_csv(self.output_df_fn,index=False)

    def process_case_id(self,case_id,overwrite=False):
        row =T.df_out.loc[T.df_out.image_id==case_id].copy()
        row = row.iloc[0]
        return self._process_row(row, overwrite)
    def process_idx(self,idx,overwrite):
        row = self.df_out.loc[idx].copy()
        return self._process_row(row, overwrite)
    def _process_row(self,row, overwrite=False):
        case_id = row['image_id']
        img_fn , lm_fn= self.create_filenames(row)

        if any([f.exists() for f in [img_fn,lm_fn]]) and overwrite==False:
            print("Files exist for ",case_id)
            return row,img_fn,lm_fn,0 
        print("Processing", case_id)
        case_fldr = [fldr for fldr in self.case_fldrs if case_id in fldr.name][0]

        fldr_segs = case_fldr/("segmentations")
        fns_segs = list(fldr_segs.glob("*"))

        exclude =  row.exclude

        eligible = self.meta_labels.location.apply(lambda x:  x  not in exclude)
        elig_labels = self.meta_labels.loc[eligible]
        fns_segs_cmp = [fn for fn in fns_segs if strip_extension(fn.name) in list(elig_labels.structure)]
        zero_lm_fns = list(set(fns_segs).difference(fns_segs_cmp))

        try:
            lms_zeros = self.load_lms(zero_lm_fns)
            lms_labelled = self.load_lms(fns_segs_cmp)
            lm_out,_= self.merge_lms(lms_labelled)
            lm_zeros , unexpected= self.merge_lms(lms_zeros,debug=True)
        except RuntimeError as erro:
            print(erro)
            row['unexpected']="Buggy lms"
            return row,img_fn,lm_fn,0

        row['unexpected']=unexpected
        if len(unexpected)==0:
            self.save_img_lm(case_fldr, img_fn,lm_out, lm_fn)
        return row,img_fn,lm_fn, lm_zeros


    def create_filenames(self,row):
        case_id = row['image_id']
        fn_out = "totalseg_"+case_id+".nii.gz"
        img_out = self.imgs_fldr/fn_out
        lm_out =  self.masks_fldr/fn_out
        return img_out,lm_out

    def load_lms(self,fns_segs):
        lms = []
        for ind in range(len(fns_segs)):
            fn = fns_segs[ind]
            dest_lab = self.meta_labels [strip_extension(fn.name) == self.meta_labels.structure].label.item()
            # print("Loading label", dest_lab)
            lm0 = sitk.ReadImage(fn)
            lm0 = to_label(lm0)
            lm0 = sitk.ChangeLabelLabelMap(lm0,{1:dest_lab})
            lms.append(lm0)
        return lms

    def merge_lms(self,lms,debug=False):
        if len(lms)>1:
            lmout = fl.reduce(sitk.MergeLabelMap,lms)
        elif len(lms)==1:
            lmout = lms[0]
        else:
            return lms, 0
        unexpected = np.nan
        if debug==True:
            labs = get_labels(lmout)
            print("Unexpected labels: ", labs)
            if len(labs)>0:
                print("----------------------Unexpected labels", labs)
                unexpected = str(labs)
        lmout = to_int(lmout)
        return lmout,unexpected

    def save_img_lm(self, case_fldr,img_outname, lm,lm_fn):
        img_fn = Path(case_fldr)/("ct.nii.gz")
        print ("Saving files for case_id: ",case_fldr.name)
        shutil.copy(img_fn,img_outname)
        sitk.WriteImage(lm,lm_fn)

# %%
if __name__ == "__main__":
        fldr = Path("/s/datasets_bkp/totalseg")
        output_fldr = Path("/s/xnat_shadow/totseg/")
        # row = T.process_case_id(id,overwrite=True)
        # row = T.process_idx(52,overwrite=True)
        # T.process_dataset(overwrite=False)
        bugs = pd.read_csv("/s/datasets_bkp/totalseg/bugs_2.csv")
        case_ids = bugs.image_id
        T = TotalSegMerger(fldr,output_fldr, case_ids)

        T.process_dataset(overwrite=True)

# %%

        imgs_fldr = Path("/s/xnat_shadow/totseg/masks/")
        imgs = list(imgs_fldr.glob("*"))
        import os
        for cid in case_ids: 
         
            fn1 = [fn for fn in imgs if cid in fn.name][0]
            os.remove(fn1)

# %%
# %%

