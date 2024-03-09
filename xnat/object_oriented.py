
# %%

import os,re
from shutil import SameFileError
from pydicom import dcmread
from typing import Union
from fastcore.basics import listify, store_attr
import pandas as pd
import itertools as il
import SimpleITK as sitk
import ipdb
import shutil
from fran.utils.imageviewers import ImageMaskViewer

from fran.utils.imageviewers import view_sitk
from fran.utils.string import cleanup_fname, info_from_filename
tr = ipdb.set_trace
from fastcore.basics import GetAttr, patch_to
from pathlib import Path
from bs4 import BeautifulSoup as BS
from bs4.element import Tag
from pyxnat import Interface
from pyxnat.core.resources import Subject, Experiment, Scan, Project
from fran.utils.helpers import  pat_nodesc

from fran.utils.fileio import load_file, load_xml, load_yaml, maybe_makedirs, save_xml, str_to_path
from xnat.helpers import fix_filename, fn_to_attr, readable_text
import itertools as il
import errno


from contextlib     import closing

def login():
    xnat_fn = os.environ["XNAT_CONFIG_PATH"]
    xnat_settings= load_yaml(xnat_fn)
    central = Interface(server=xnat_settings['server'], user=xnat_settings['user'], password=xnat_settings['password'])
    return central, xnat_settings['xnat_shadow_folder']

class _XMLObj(GetAttr):
    _default = 'src'

    def __init__(self,src):

        if not isinstance(src,Union[BS,Tag]): src = BS(src,features="xml")
        store_attr()

    def __repr__(self) -> str:
            repr = self.src.__repr__()
            return repr


    def __getitem__(self,key):
        val = self.find_all(key)
        return val

class ExpXML(_XMLObj):
    @property
    def date(self):
        date = self.src.find(["xnat:date"]).string
        date = date.replace('-','')
        return date

    def get_uri(self,label):
        # exp= sub.exps[j]
        # x=exp.x
        files =self['xnat:file'] 
        image_tag = [f for f in files if f['label'] == label][0]
        xml_fn= Path(image_tag['URI'])
        parent_fldr = xml_fn.parent
        aa = load_xml(xml_fn)
        cat = aa.find_all("cat:entry")
        fns = [parent_fldr/(cc.attrs['URI']) for cc in cat]
        if len(fns)==1:
            return fns[0]
        else:
            return fns

    # def __repr__(self) -> str:
    #     return print(self.src)

class FilesetXML(_XMLObj):
    def __init__(self, src):
        super().__init__(src)
        self.format  = self.src['format']
        self.label  = self.src['label']
        self.uri =  Path(self.src['URI'])
        self.fldr = self.uri.parent
        self.x =  load_xml(self.uri)
        self.fpaths = self.get_fpaths()

    def get_fpaths(self):
        fpaths =[]
        cats = self.x.find_all(['cat:entry'])
        for cat in cats:
            fname = cat['URI']
            fpath = self.fldr/fname
            if fpath.exists():
                fpaths.append(str(fpath))
            else:
                fpath = fpath.str_replace("nrrd","nii.gz")
                fpaths.append(str(fpath))
                if not fpath.exists():
                    raise FileNotFoundError(
                        errno.ENOENT, os.strerror(errno.ENOENT), str(fpath))
        return fpaths

    def __len__(self) : return len(self.get_fpaths)



class ScnXML(_XMLObj):
    def __init__(self, src):
        super().__init__(src)
        self.filesets= [FilesetXML(x) for x in self.find_all(['xnat:file'])]

    def __repr__(self) -> str:
        return super().__repr__()


#
#     def __init__(self,src): 
#         super().__init__(src)
#         
#         store_attr()

class _BaseObj(GetAttr):
    _default = 'esp'
    def __init__(self,esp) -> None:
        store_attr()

    def __repr__(self) -> str: 
            return self.esp.__repr__()

    def add_rsc(self,fpath, label,content="CT",format="NIFTI",tags=[],force=False):
        fname = fpath.name

        if self.has_rsc(label) and force==True:
            self.del_rsc(label)
        if not self.has_rsc(label):
            rsc_neo = self.resource(label)
            if len(tags)>0:
                for tg in tags:
                    rsc_neo.tag(tg)
            rsc_neo.file(fname).put(fpath,
                                    content= content,
                                    format=format)
            # rsc_neo.create()
            print("Resource labelled {0} added from filepath: {1}".format(label,fpath))
        else : print("Resources labelled {} already exists. Nothing to do.".format(label))

    def has_rsc(self,label:str):
        rec= self.resource(label)
        return rec.exists()
    def del_rsc(self,label:str):
        rec = self.resource(label)
        if rec.exists()==True:
            rec.delete()
            print("Resource {0} delete".format(label))
        else:
            print("Resource {0} does not exist. Nothing to delete.".format(label))

class _ExpScn(_BaseObj):
    _default = 'esp'
    def __init__(self,pt_id,esp) -> None:
        super().__init__(esp)
        store_attr('pt_id')

class Proj(_BaseObj):
    def __init__(self, proj_title:str) : 
        central , xnat_shadow_folder= login()
        self.export_folder = Path(xnat_shadow_folder)/proj_title
        esp = central.select.project(proj_title)
        print("Project {0} exists: {1}".format(proj_title, esp.exists()))
        super().__init__(esp)
        self.subs = self.get_subs_all()

    def get_subs_all(self):
        subs = self.esp.subjects()
        subs = [Subj(scn) for scn in subs]
        return subs

    def get_subs_with_rsc(self,label="MASK"):
        subs_with_rsc=[]
        for ss in self.subs:
            rscs = ss.rscs
            mask_present = any([r.label()==label for r in rscs])
            if mask_present==True:
                subs_with_rsc.append(ss)
        return subs_with_rsc

    def delete_rscs(self,label="IMAGE"):
        '''
        delete recursively all resources with label in all 'scans'
        '''
       
        subs = self.subs
        for ss in subs:
            for rsc in ss.rscs:
                if rsc.label()==label:
                    print("Deleteting resource {0}".format(rsc))
                    rsc.delete() 

    def create_report(self,mask_label="MASK_THICK") -> pd.DataFrame:
        img_label = mask_label.replace("MASK","IMAGE")
        csv_label ="IMAGE_MASK_FPATHS"
        ss = self.get_subs_with_rsc(mask_label)
        img_fpaths,mask_fpaths=[],[]
        for scn in ss:
                scns = [scn for scn in scn.scans if scn.has_rsc(mask_label)]
                for sc in scns:
                    mask_fpaths.append(sc.get_rsc_fpaths(mask_label)[0])
                    img_fpaths.append(sc.get_rsc_fpaths(img_label)[0])
        tmp = list(zip(img_fpaths,mask_fpaths))
        df = pd.DataFrame(tmp, columns = ["img_fpaths","mask_fpaths"])
        csv_fn = Path("/tmp/img_mask_fpaths.csv")
        df.to_csv(csv_fn,index=False)
        self.add_rsc(csv_fn,label=csv_label,content="CSV",format="CSV",force=True)
        return df

    def create_report2(self,mask_label="MASK_THICK") -> pd.DataFrame:
        img_label = mask_label.replace("MASK","IMAGE")
        csv_label ="IMAGE_MASK_FPATHS"
        ss = self.get_subs_with_rsc(mask_label)
        img_fpaths,mask_fpaths=[],[]
        for scn in ss:
                scns = [scn for scn in scn.scans if scn.has_rsc(mask_label)]
                for sc in scns:
                    xm = sc.x
                    fs = xm.find_all("xnat:file")
                    labels = [f['label'] for f in fs]
                    if img_label in labels and mask_label in labels:
                        img_x = [f for f in fs if f['label'] ==img_label][0]
                        mask_x = [f for f in fs if f['label'] ==mask_label][0]
                        mask_fpath = self._fpath_from_catalog(mask_x)
                        img_fpath = self._fpath_from_catalog(img_x)
                        mask_fpaths.append(str(mask_fpath))
                        img_fpaths.append(str(img_fpath))
        tmp = list(zip(img_fpaths,mask_fpaths))
        df = pd.DataFrame(tmp, columns = ["img_fpaths","mask_fpaths"])
        csv_fn = Path("/tmp/img_mask_fpaths.csv")
        df.to_csv(csv_fn,index=False)
        self.add_rsc(csv_fn,label=csv_label,content="CSV",format="CSV",force=True)
        return df

    def _fpath_from_catalog(self,xm):
                        cat_m = Path(xm['URI'])
                        fldr = cat_m.parent
                        cat_mx= load_xml(cat_m)
                        entry = cat_mx.find_all("cat:entry")[0]
                        fpath = fldr/entry['URI']
                        return fpath


    def export_nii(self,symlink=True,overwrite=False):
        '''
        Project must already have the csv_file resource "IMAGE_MASK_FPATHS"
        '''
        rc = self.resource("IMAGE_MASK_FPATHS")
        csv_fn = rc.get("/tmp/", extract=True)[0]
        df = pd.read_csv(csv_fn)
        fldrs = self.export_folder/"images", self.export_folder/"masks"
        [maybe_makedirs(f) for f in fldrs]
        filesets=  df.img_fpaths, df.mask_fpaths
        fnc = os.symlink if symlink==True else shutil.copy
        for fldr,files in zip(fldrs,filesets):
            self._cp_files(files,fldr,fnc,overwrite)

    def _cp_files(self,files,fldr,fnc,overwrite):
            for f in files:
                f = Path(f)
                outfname = fldr/f.name
                if overwrite == True and outfname.exists(): os.remove(outfname)
                try:
                   
                    fnc(f,outfname)
                    print("Creating copy/link: {0}----> {1}".format(f,outfname))
                except FileExistsError:
                    print("File {} exists. Skipping".format(outfname))
                except SameFileError:
                    print("File {} exists. Skipping".format(outfname))


        



class Subj(GetAttr):
    _default= 'scn'
    def __init__(self,scn:Subject):
        assert isinstance(scn,Subject),"Initialize with a Subject instance please"
        store_attr() 
        self.exp_ids = self.scn.experiments().get()
        self.get_rscs()


    def exp(self, id:Union[str,int]):
        if isinstance(id,int):
            id = self.exp_ids[id]
        exp = self.scn.experiment(id)
        return Exp(self.get_pt_id(), exp)

    def download_rscs(self,labels,dest_folder):
        labels =listify(labels)
        for label in labels:
            rscs = [r for r in self.rscs if r.label() == label]
            for r in rscs:
                r.get(dest_folder,extract=True)

    @property
    def exps(self):
        exps = [self.exp(id) for id in self.exp_ids]
        return exps

        exps = [ss.exp(id) for id in ss.exp_ids]
    @property
    def scans(self):
        scans = [exp.scans for exp in self.exps]
        scans = list(il.chain.from_iterable(scans))
        return scans

    def get_rscs(self):
        r=[]
        rscs_s = [scn.resources() for scn in self.scans]
        rscs_r = [scn.resources() for scn in self.exps]
        for rsc_set in rscs_r+ rscs_s:
          r.append([Rsc(rr) for rr in rsc_set])
        self.rscs = list(il.chain.from_iterable(r))


    @property
    def project(self):
        project = self.scn.shares()[0]
        return project.label()

    def get_pt_id(self,append_proj=True):
        pt_id = self.scn.label()
        if append_proj==True:
            return self.project+"_"+pt_id
        else:
            return pt_id

    @classmethod
    def from_pt_id(cls,pt_id,proj_title):

        central , _ = login()
        subj = central.select.project(proj_title).subject(pt_id)
        return cls(subj)

    def __repr__(self):
        return self.get_pt_id()

class Rsc(GetAttr):
    _default='r'
    def __init__(self,r):store_attr()
    def __repr__(self) -> str: 
            repr = self.r.__repr__()+"parent: "+self.r.parent().datatype()
            return repr



class Exp(_ExpScn):
    def __init__(self,pt_id, esp:Experiment):
        assert isinstance(esp,Experiment),"Initialize with a Experiment instance please"
        super().__init__(pt_id,esp)
        self.x = ExpXML(self.get())
        self.scans = [Scn(pt_id,scn ) for scn in self.esp.scans()]

    @property
    def date(self):
        return self.x.date


class Scn(_ExpScn):
    def __init__(self,pt_id, esp:Scan) -> None:
        assert isinstance(esp,Scan),"Initialize with a Scan instance please"
        super().__init__(pt_id,esp)
        self.x = ScnXML(self.get())
        self.filesets = self.x.filesets

    def parent(self): return Exp(self.pt_id,self.esp.parent())

    def get_filesetXML(self,label:str):
        try:
            assert self.has_rsc(label),"Resource {0} does not exist. No fileset to get".format(label)
            fs= [f for f in self.filesets if f.label == label][0]
            return fs
        except AssertionError as msg:
            print(msg)


    def get_rsc_fpaths(self,label:str):
        fs = self.get_filesetXML(label)
        return fs.get_fpaths()

    def nii_postprocess(self,rsc_label:str,output_label:str,fnc,*fncargs:None):
        '''
        Finds nii resources of {rsc_label}, applies fnc, and stores output with output_label
        fnc should have by design an input_fname, output_fname and any number of fnckwargs
        for now , this script is creating output_fnames
        '''
        fpath = self.get_rsc_fpaths(rsc_label)
        try:
            assert(len(fpath)==1),"More than one nii file with label: {0}".format(rsc_label)
            fpath = Path(fpath[0])
        except Exception as e:
            raise e
        try:
            assert(self.has_rsc(output_label)==False), "Resource {} already exists. Skipping..".format(output_label)
            out_fname =  fpath.name.replace(".nii","_thick.nii.gz") 
            out_fname= out_fname.replace(".gz.gz",".gz")
            out_fullpath = Path("/tmp")/out_fname
            img = fnc(fpath,*fncargs)
            sitk.WriteImage(img,out_fullpath)
            self.add_rsc(fpath=out_fullpath,label=output_label)
        except Exception as e:
            print(e)

            
    def dcm2nii(self,label="IMAGE", desc_in_fname=True, overwrite=False):

        if not self.has_rsc(label) or overwrite==True:
            dcm_fn1= self.dcm_fns[0]
            fldr = Path(dcm_fn1).parent
            nii_fname = self.generate_nii_fname(dcm_fn1,desc_in_fname)
            reader = sitk.ImageSeriesReader()
            dcm_names = reader.GetGDCMSeriesFileNames(str(fldr))
            reader.SetFileNames(dcm_names)
            img = reader.Execute()
            tmp_nm= Path("/home/ub/.tmp/{0}".format(nii_fname))
            sitk.WriteImage(img,tmp_nm)
            self.add_rsc(fpath = tmp_nm, label=label)
        else:
            print("Case id {0}, Desc: {1}. However, resource labelled {2} already exists. Nothing to do.".format(self.pt_id,self.desc,label))

    def generate_nii_fname(self,dcm_file, desc_in_fname=True):
        date = self.date
        hdr = dcmread(dcm_file)
        desc = hdr.SeriesDescription
        desc = readable_text(desc)
        if desc not in self.pt_id and desc_in_fname==True:  
            fname = "_".join([self.pt_id,date,desc])+".nii.gz"
        else:
            fname = "_".join([self.pt_id,date])+".nii.gz"

        return fname

    @property
    def date(self): return self.parent().date
    #attrs = ['ID', 'type', 'frames', 'quality']
    

    @property
    def desc(self):
        return self.attrs.get("type")

    @property
    def dcm_fns(self):
            dcm_fs= self.get_filesetXML('DICOM')
            self._dcm_fns  =dcm_fs.get_fpaths()
            return self._dcm_fns


 
def upload_nii(fpath,has_date=True,fpath_tags=['case_id'], xnat_tags:list=[], label=""):
        '''
        retrieves project_id, pt_name, and scan from fpath and adds it as a resource
        '''
        
        exps = fname_to_exp(fpath.name,has_date=has_date)
        scans_matched=[]
        for e in exps:
            for scn in e.scans:
                desc ,date= readable_text(scn.desc), scn.date
                outputs = info_from_filename(fpath.name)
                odesc , odate= outputs['desc'], outputs['date']
                if desc.lower()==odesc.lower() and date == odate:
                    print("Matching CT scan found: date {0} id {1}".format(e.date, scn.id()))
                    scans_matched.append(scn)
        if len(scans_matched)!=1: 
            tr()
        scan_matched = scans_matched[0]
        scan_matched.add_rsc(fpath,label=label,tags=xnat_tags)
       

def upload_nii_nodesc(fpath:Union[str,Path],label,tags:list=[]):
        '''
        retrieves project_id, pt_name. Without description given, it uploads the nii to the first scan in exp.scans list
        '''

        exps = fname_to_exp(fpath)
        if len(exps)!=1:
            print("Not sure which experiment to upload this file to!")
            tr()
        e = exps[0]

        try:
            scn = e.scans[0]
            scn.add_rsc(fpath,label=label,tags=tags)
        except:
            print("Unmatched file: {0}\n pt: {1}\nscan date: {2}".format(fpath, scn.pt_id,scn.date))

# fpath2 = Path("/home/ub/tmp/LIDC_0078.nii.gz")
def fname_to_exp(fname:str, has_date:bool):
        info = info_from_filename(fname)
        proj_title, case_id =info['proj_title'], info['case_id']
        sub = Subj.from_pt_id(case_id,proj_title)
        exp_matched=[]
        if has_date==True:
            date = info['date']
            for exp in sub.exps:
                if exp.date ==date:
                    exp_matched.append(exp)
        else:
            exps = sub.exps[0]
        return exp_matched

@str_to_path(0)
def get_matching_rsc(fpath,target_label="IMAGE"):
    exps = fname_to_exp(fpath)
    for e in exps:
        scn = e.scans[0]
        rs = scn.resources()
        rr = scn.get_rsc_fpaths(target_label)
        if len(rr)!=1: tr()
        rr = Path(rr[0])
        if  cleanup_fname(rr.name)!= cleanup_fname(fpath.name): tr()
        return rr







# %%
if __name__ == "__main__":
        
    proj_title = 'lidc_unable_to_delete'
    proj = central.select.project(proj_title)
    proj.exists()
    proj = Proj(proj_title)
    label = "MASK"

    proj.has_rsc('MASK')
    # df = proj.create_report()
# %%

    rc = proj.resource("IMAGE_MASK_FPATHS")
    rc.get("/home/ub/Desktop", extract=True)
    ss = proj.get_subs_with_rsc(label)
# %%
    rc = proj.resource("IMAGE_MASK_FPATHS")
    csv_fn = rc.get("/tmp/", extract=True)[0]
    df = pd.read_csv(csv_fn)
    output_parent = proj.xnat_shadow_folder
    fldrs = [output_parent/"images", output_parent/"masks"]
    filesets = df.img_fpaths, df.mask_fpaths
    maybe_makedirs(fldrs)
# %%
    consts = [
        ("xnat:subjectData/SUBJECT_ID","LIKE","XNAT_S01274"),
        # ("xnat:subjectData/label","=",case_id),
    ]
    ex = central.select('xnat:subjectData').where(consts)
    ss = central.select("//subject").where(consts)
    ss = central.select("/project/lidc/subject/LIDC_0078")
    ss = central.select("/project/lidc0/subjects")

    s.delete()
# %%
    for s in ss:
        try:
            s.delete()
        except:
            exps = s.experiments()
            for exp in s.experiments():
                try:
                    tr()
                    exp.delete()
                except:
                    pass
# %%
        


# %%

# %%
    fldr_i = Path("/scn/datasets_bkp/litq/sitk/images")
    fldr = Path("/home/ub/Desktop/capestart/liver/masks_all_liver_capestart/orphan_masks/")
    fldr=Path("/home/ub/Desktop/capestart/nodes/output_orphans/")
# %%

    files = list(fldr.glob("*"))
    for fpath in files:
        if fpath.is_file():
            upload_nii(fpath,label="IMAGE_THICK")

# %%
    fpath=files[0]

    fname = fpath.name
    pat_full = r"(?P<pt_id>[a-z]*_[a-z0-9]+)_(?P<date>\d+)_(?P<desc>.*)_(?P<tag>thick)?_?.*(?=(?P<ext>\.(nii|nrrd)(\.gz)?)$)"
    fname = cleanup_fname(fname)
    f2 = 'nodes_44_20220805_1mmBody2p000NeckStandardArterialCoronalCE_thick.nii.gz'
    m = re.match(pat_full,f2)
    m.groups()

    parts = fname.split("_")
    proj_title= parts[0]
    pt_id = "_".join(parts[:2])
    date = parts[2]
     
    output = [parts[0],parts[1]]
# %%
    fn  = fname

    fname = fn.name
    name = cleanup_fname(fname)

    parts = name.split("_")
    proj_title = parts[0]
    case_id = "_".join(parts[:2])
    outputs=[proj_title,case_id]

    out = info_from_filename(fname)
    
