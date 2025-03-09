# %%

from pathlib import Path
import shutil
import ipdb
tr = ipdb.set_trace

from utilz.fileio import maybe_makedirs, str_to_path
import re

def readable_text(txt):
    # without extension please!
    badchars ={
        "&":"",
        "/":"",
        "+":"",
        ".":"p",
        " ":"",
        ",":"",
        "(":"",
        ")":"",
        "_":"",
    }
    rep = dict((re.escape(k), v) for k, v in badchars.items()) 
    pattern = re.compile("|".join(rep.keys()))
    txt= pattern.sub(lambda m: rep[re.escape(m.group(0))], txt)
    txt = [txt.replace(k,v) for k,v in badchars.items()][0]
    return txt

# %%
def fn_to_attr(fpath: Path):
    '''
    Parse filename into components: patient ID, date, description, tag and extension.
    
    Args:
        fpath (Path): Path object containing filename to parse
        
    Returns:
        tuple: (pt_id, date, desc, tag, ext) if successful
        None: if parsing fails
        
    Example:
        "sub_001_20230615_T1w_thick.nii.gz" ->
        ("sub_001", "20230615", "T1w", "thick", ".nii.gz")
    '''
    fpath = fpath.name
    
    # Main pattern with all components
    PAT_FULL = r"(?P<pt_id>[a-z]*_[a-z0-9]+)_(?P<date>\d+)_(?P<desc>[^_]+)_(?P<tag>[^_\.]+).*(?P<ext>\.(nii|nrrd)(\.gz)?$)"
    
    # Fallback patterns
    PAT_NODESC = r"(?P<pt_id>[a-z]*_[a-z0-9]+)_(?P<date>\d+)(?P<ext>\.(nii|nrrd)(\.gz)?$)"
    PAT_IDONLY = r"(?P<pt_id>[a-z]*_[a-z0-9]+)(?P<ext>\.(nii|nrrd)(\.gz)?$)"
    
    # Try patterns in order of most to least specific
    for pattern in [PAT_FULL, PAT_NODESC, PAT_IDONLY]:
        match = re.match(pattern, fpath, re.IGNORECASE)
        if match:
            groups = match.groupdict()
            return (
                groups.get("pt_id", ""),
                groups.get("date", ""),
                groups.get("desc", ""),
                groups.get("tag", ""),
                groups.get("ext", "")
            )
            
    return None  # Return None if no pattern matches
   
# %%
def fix_filename(fpath):
    '''
    legacy readable_text allowed _num_ formats to circumvent (num). This created fnames with unnecessary _ in them. This function fixes names

    '''
    components = fn_to_attr(fpath)
    desc = components[2]
    no_undrscr= desc.replace("_","")
    if no_undrscr!=desc:
        print("Changing filename component: "+desc+" to --->"+no_undrscr)
        components[2]= no_undrscr
        fname =   "_".join(components[:-2])+components[-2]
        fname_out = fpath.parent/(fname)
        print(fname_out)
        shutil.move(fpath,fname_out)


@str_to_path([0,1])
def collate_nii_foldertree(src_fldr,dest_fldr,fname_cond:str=""):
    '''
    This function searches for all files recursively under src_fldr and moves them to dest_fldr. If an fname_cond is set, only files with that substring will be moved.
    '''
    
    maybe_makedirs([dest_fldr])
    ni = list(src_fldr.rglob("*"))
    ni = [n for n in ni if n.is_file() and fname_cond in n.name]
    print("{0} files found".format(len(ni)))
    print("Moving all files from  {0} to  {1}".format(str(src_fldr), str(dest_fldr)))
    for fn in ni:
            fn_neo =dest_fldr/fn.name
            print("{0}   ---->   {1}".format(fn,fn_neo))
            shutil.move(fn,fn_neo)





# %%
# %%

# %%
if __name__ == "__main__":
    imgs_fldr = "/s/xnat_shadow/crc/test/images/"
    dest = Path(imgs_fldr)/"tmp"
    collate_nii_foldertree(imgs_fldr,dest,fname_cond="")
# %%
