# %%
from dicom_utils.metadata import *
import pyxnat
import itertools as il
import os
import re
import shutil
from shutil import SameFileError
from typing import Union

import ipdb
import numpy as np
import pandas as pd
import SimpleITK as sitk
from fastcore.basics import listify, store_attr
from label_analysis.helpers import get_labels
from pydicom import dcmread

from dicom_utils.drli_helper import dcm_segmentation
from fran.utils.imageviewers import ImageMaskViewer, view_sitk
from fran.utils.string import cleanup_fname, info_from_filename

tr = ipdb.set_trace
import errno
import itertools as il
from pathlib import Path

from bs4 import BeautifulSoup as BS
from bs4.element import Tag
from fastcore.basics import GetAttr, patch_to
from pyxnat import Interface
from pyxnat.core.resources import Experiment, Project, Scan, Subject
from xnat.helpers import fix_filename, fn_to_attr, readable_text

from fran.utils.fileio import (load_file, load_xml, load_yaml, maybe_makedirs,
                               save_xml, str_to_path)
from fran.utils.helpers import get_pbar, pat_nodesc

pbar= get_pbar()
XNAT_TMP_FLDR="/s/tmp/xnat"

from contextlib import closing

def is_lm(label):
    candidates = ["MASK", "LABEL","LM"]
    if any ([x in label for x in candidates]):
        return True
    else:
        return False

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
        # self.filesets= [FilesetXML(x) for x in self.find_all(['xnat:file'])]

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
            rsc_neo.file(fname).insert(fpath,
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
        self.name = proj_title
        central , xnat_shadow_folder= login()
        self.export_folder = Path(xnat_shadow_folder)/proj_title
        esp = central.select.project(proj_title)
        print("Project {0} exists: {1}".format(proj_title, esp.exists()))
        super().__init__(esp)
        # self.subs = self.get_subs_all()

    def get_subs_all(self):
        subs = self.esp.subjects()
        subs = [Subj(scn) for scn in subs]
        return subs

    def get_subs_with_rsc(self,label="MASK"):
        subs_with_rsc=[]
        for ss in self.subs:
            ss= Subj(ss)
            rscs = ss.rscs
            mask_present = any([rsc.label()==label for rsc in rscs])
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

    @property
    def subs(self): return self.subjects()
    # def create_report(self,mask_label="MASK_THICK") -> pd.DataFrame:
    #     img_label = mask_label.replace("MASK","IMAGE")
    #     csv_label ="IMAGE_MASK_FPATHS"
    #     ss = self.get_subs_with_rsc(mask_label)
    #     img_fpaths,mask_fpaths=[],[]
    #     for scn in ss:
    #             scns = [scn for scn in scn.scans if scn.has_rsc(mask_label)]
    #             for sc in scns:
    #                 mask_fpaths.append(sc.get_rsc_fpaths(mask_label)[0])
    #                 img_fpaths.append(sc.get_rsc_fpaths(img_label)[0])
    #     tmp = list(zip(img_fpaths,mask_fpaths))
    #     df = pd.DataFrame(tmp, columns = ["img_fpaths","mask_fpaths"])
    #     csv_fn = Path("/tmp/img_mask_fpaths.csv")
    #     df.to_csv(csv_fn,index=False)
    #     self.add_rsc(csv_fn,label=csv_label,content="CSV",format="CSV",force=True)
    #     return df
    #
    def collate_metadata(self):
        cols = 'case_id','filename', 'date', 'vendor','model','kernel','filter_type','kvp','current' , 'exposure','ctdi','thickness'
        tag_list =vendor,model ,kernel,filter_type,kvp,current, exposure,ctdi,thickness
        all_exps=[]
        subs = list(self.subs)
        for i in pbar(range(len(subs))):
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

        df = pd.DataFrame(data=all_exps,columns = cols)
        rsc_name = "dcm_metadata"
        self.df_rsc(df,rsc_name)


    def df_rsc(self,df,rsc_name):
        csv_fn = Path("/tmp/{}.csv".format(rsc_name))
        df.to_csv(csv_fn,index=False)
        self.add_rsc(csv_fn,label=rsc_name,content="CSV",format="CSV",force=True)

    def create_report(self, add_label_info=True) -> pd.DataFrame:
        '''
        add_label_info: add label info to the report. Slows it down
        '''
        excluded_labels =['DICOM'] # makes a v large df
        if 'no-dicom' in self.keywords: 
            search_level = 'exps'
            tag = "resource"
        else:
            search_level = 'scans'
            tag = "file"
        csv_label ="RESOURCES"
        print("Adding filepath info")
        df =[]
        for sub in pbar(self.subs):
                sub = Subj(sub)
                dici = sub.get_info()
                ses = getattr(sub,search_level)
                for se in ses:
                    xm = se.x
                    fs = xm.find_all(f"xnat:{tag}")
                    for f in fs:
                        label = f['label']
                        if label not in excluded_labels :
                            fpath = self._fpath_from_catalog(f)
                            dici2 = {'label':label,'fpath':fpath}
                            if add_label_info==True:
                                dici2 = self.maybe_add_labels(label,fpath,dici2)
                            dici_final = dici|dici2
                            df.append(dici_final)
        df = pd.DataFrame(df)

        rsc_name = "Resources"
        self.df_rsc(df,rsc_name)
        return df

    def maybe_add_labels(self,label,fpath,dici):
        if  is_lm(label)==True:
            dici['label_info'] = self.get_label_info([fpath])
        return dici


    def get_label_info(self,mask_fnames):
        labels=[]
        print("Adding label info")
        for mask_fn in pbar(mask_fnames):
            lm = sitk.ReadImage(mask_fn)
            labs=get_labels(lm)
            if len(labs)==0:
                labs= np.nan
            labels.append(labs)
        return labels


    def _fpath_from_catalog(self,xm):
                        cat_m = Path(xm['URI'])
                        fldr = cat_m.parent
                        cat_mx= load_xml(cat_m)
                        entry = cat_mx.find_all("cat:entry")[0]
                        fpath = fldr/entry['URI']
                        return fpath


    def dcm2nii(self,add_date,add_desc,overwrite):
        for i,sub in enumerate(self.subs):
            sub = Subj(sub)
            for scn in sub.scans:
                scn.dcm2nii(add_date=add_date,add_desc=add_desc,overwrite=overwrite)


    def export_nii(self,symlink=True,overwrite=False,ensure_fg=True):
        '''
        Project must already have the csv_file resource "IMAGE_MASK_FPATHS"
        '''
        rc = self.resource("IMAGE_MASK_FPATHS")
        csv_fn = rc.get("/tmp/", extract=True)[0]
        df = pd.read_csv(csv_fn)
        if ensure_fg==True:
            df.dropna(inplace=True)
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


    @property
    def keywords(self):
        c, _ = login()
        const = [
            ('xnat:projectData/name','=',self.name)
        ]
        aa=    c.select('xnat:projectData',
                 [
                # 'xnat:projectData/name',
                 'xnat:projectData/keywords'
                 ]
                        ).where(const)
        try:
            kw = aa[0]['keywords']
            return kw
        except:
            return ''


        



class Subj(GetAttr):
    _default= 'scn'
    def __init__(self,scn:Subject):
        assert isinstance(scn,Union[pyxnat.core.resources.Subject,Subject]),"Initialize with a Subject instance please"
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
            rscs = [rsc for rsc in  self.rscs if rsc.label() == label]
            for rsc in rscs:
                rsc.get(dest_folder,extract=True)


    @property
    def test(self):
        test = self.attrs.get("ethnicity")

    @test.setter
    def test(self,value):
        assert value in ["test","train"], "Must be 'test' or 'train'"
        self.attrs.set('ethnicity',value)



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
        rscs_r = [exp.resources() for exp in self.exps]
        for rsc_set in rscs_r+ rscs_s:
          r.append([Rsc(rr) for rr in rsc_set])
        self.rscs = list(il.chain.from_iterable(r))


    def get_info(self):
        c,_ = login()
        subject_id = self.id()
        pt_id = self.get_pt_id()
        columns = ['xnat:subjectData/PROJECT',
                   'xnat:subjectData/SUBJECT_ID',
                   'xnat:subjectData/INSERT_DATE',
                   'xnat:subjectData/GENDER_TEXT',
                   'xnat:subjectData/ETHNICITY',]

        dt = 'xnat:subjectData'
        data = c.select(dt, columns=columns).all().data
        c._subjectData = data
        data = [e for e in data if e['subject_id'] == subject_id][0]
        data["case_id"] =pt_id
        self._info = data
        return self._info



    @property
    def project(self, use_alias=True):
        # use_alias allows me to use alias when project title does not conform with naming convention i use in my projects.
        project = self.scn.shares()[0]
        if use_alias==True and len(project.aliases())>0:
            return project.aliases()[0]
        else:
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


def resolve_scan_object(datatype):
            modalities = 'xnat:ctScanData', 'xnat:mrScanData'
            if datatype == "xnat:segScanData":
                scnobj = ScnSeg
            elif datatype in modalities:
                scnobj = Scn
            else:
                tr()
            return scnobj
            
            
class Exp(_ExpScn):
    def __init__(self,pt_id, esp:Experiment):
        assert isinstance(esp,Experiment),"Initialize with a Experiment instance please"
        super().__init__(pt_id,esp)
        self.x = ExpXML(self.get())
        scns = self.esp.scans()
        self.scans=[]
        for scn in scns:
            scnobj = resolve_scan_object(scn.datatype())
            scan = scnobj(pt_id,scn)
            self.scans.append(
                scan

            )

    @property
    def date(self):
        return self.x.date


class Scn(_ExpScn):
    def __init__(self,pt_id, esp:Scan) -> None:
        assert isinstance(esp,Scan),"Initialize with a Scan instance please"
        super().__init__(pt_id,esp)
        self.x = ScnXML(self.get())
        self.datatype=["DICOM"]

    def parent(self): return Exp(self.pt_id,self.esp.parent())


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

            
    def dcm2nii(self,label="IMAGE", add_date=True, add_desc=True, overwrite=False):
        self.download_dcm_fns()
        if not self.has_rsc(label) or overwrite==True:
            dcm_fn1= self.dcm_fns[0]
            nii_fname = self.generate_nii_fname(dcm_fn1,add_date, add_desc)
            tmp_nm= Path(XNAT_TMP_FLDR+"/{0}".format(nii_fname))
            try:
                img = self._sitk_convert(dcm_fn1)
                sitk.WriteImage(img,tmp_nm)
                self.add_rsc(fpath = tmp_nm, label=label)
            except ValueError as e:
                print("Error processing, pt id: ",self.pt_id)
                print(e)
                
        else:
            print("Case id {0}, Desc: {1}. However, resource labelled {2} already exists. Nothing to do.".format(self.pt_id,self.desc,label))


    def download_dcm_fns(self):
        rsc_dcm= [rs for rs in self.resources() if rs.label() in self.datatype]
        assert len(rsc_dcm)==1,"More than one DICOM resource found for {0}".format(self.pt_id)
        rsc = rsc_dcm[0]
        fldr = "/".join([XNAT_TMP_FLDR,self.pt_id])
        maybe_makedirs(fldr)
        rsc.get(fldr,extract=True)
        sub_fldr= Path("/".join([fldr,rsc.id()]))
        self.dcm_fns = list(sub_fldr.glob("*dcm"))

    def _sitk_convert(self,dcm_fn):
            reader = sitk.ImageSeriesReader()
            fldr = Path(dcm_fn).parent
            dcm_names = reader.GetGDCMSeriesFileNames(str(fldr))
            reader.SetFileNames(dcm_names)
            img = reader.Execute()
            return img


    def generate_nii_fname(self,dcm_file, date= True,desc=True):
        fname = self.pt_id
        if date==True:
            date = self.date
            fname+="_"+date
        if desc==True:
            hdr = dcmread(dcm_file)
            desc = hdr.SeriesDescription
            desc = readable_text(desc)
            fname+="_"+desc
        fname+=".nii.gz"
        return fname

    @property
    def date(self): return self.parent().date
    #attrs = ['ID', 'type', 'frames', 'quality']
    

    @property
    def desc(self):
        return self.attrs.get("type")
    #
    # @property
    # def dcm_fns(self):
    #         dcm_fs= self.get_filesetXML()
    #         self._dcm_fns  =dcm_fs.get_fpaths()
    #         return self._dcm_fns


class ScnSeg(Scn):
    def __init__(self, pt_id, esp: Scan) -> None:
        super().__init__(pt_id, esp)
        self.datatype=["secondary","Segmentation"]
    def dcm2nii(self, label="LABELMAP", add_date=True, add_desc=True, overwrite=False):
        return super().dcm2nii(label=label, add_date=add_date,add_desc=add_desc,overwrite= overwrite)

    def _sitk_convert(self,dcm_fn):
            return dcm_segmentation(dcm_fn)


 
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
    central , xnat_shadow_folder= login()
        
    proj_title = 'tciaclm'

    proj = Proj(proj_title)
    proj.dcm2nii(add_date=True,add_desc=True,overwrite=False)
    # proj.create_report()
# %%
    subs = proj.subs
    sub =subs[0]
    sub= Subj(sub)
    rscs = sub.rscs
    rsc = rscs[0]
    scn = sub.scans[0]
    scn.dcm2nii(label="IMAGE")
    pt_id = sub.get_pt_id()
# %%
    proj = central.select.project(proj_title)
    proj.exists()
    proj = Proj(proj_title)
    label = "MASK"

    proj.has_rsc('MASK')
    # df = proj.create_report()
# %%
# %%
#SECTION:-------------------- TROUBLESHOOT--------------------------------------------------------------------------------------

    sub = proj.subs[1]
    sub = Subj(sub)

    sub.exp_ids = sub.scn.experiments().get()
# %%
    sub.scans
    scn = sub.scans[0]

    x = scn.get()
    scn.x = ScnXML(x)


    central.xpath.checkout(subjects=[sub.id()])
# %%
    fs = scn.x.find_all(['xnat:file'])
    ff = fs[0]
    uri = ff['URI']
    os.chmod(uri,0o644)

    scn.x.filesets= [FilesetXML(x) for x in fs ]
# %%

    self.format  = self.src['format']
    self.label  = self.src['label']
    self.uri =  Path(self.src['URI'])
    self.fldr = self.uri.parent
    self.x =  load_xml(self.uri)
    self.fpaths = self.get_fpaths()
# %%
    scn.x = ScnXML(scn.get())
    scn.filesets = scn.x.filesets
# %%
