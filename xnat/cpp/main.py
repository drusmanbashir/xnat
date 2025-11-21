# %%
import os
import shutil
import time
from pathlib import Path

import itk
from dicom_utils.helpers import dcm_segmentation
from label_analysis.utils import fix_slicer_labelmap, get_metadata, thicken_nii
from tqdm import tqdm
from utilz.fileio import maybe_makedirs

from xnat.helpers import collate_nii_foldertree
from xnat.object_oriented import *
from xnat.object_oriented import Subj

# %%
if __name__ == '__main__':
    dicom_dir =Path("/media/UB/datasets/nodes/20/20/DICOM")
    dicom_files = []
    out_nii = "/tmp/nodes_20.nii.gz"
    for fn in dicom_dir.rglob("*"):
        if fn.is_file():
            # crude DICOM detection: extension or no extension
            if fn.suffix.lower() in {".dcm", ".dicom", ""}:
                dicom_files.append(str(fn))
# %%
    fldr_p = Path(dicom_files[0]).parent
    name_gfe= itk.GDCMSeriesFileNames.New()
    name_gfe.SetUseSeriesDetails(True)
    name_gfe.SetDirectory(str(fldr_p))
    series_uids = name_gfe.GetSeriesUIDs()
    series_uid = series_uids[0]

    filenames = name_gfe.GetFileNames(series_uid)
# %%
    ImageType = itk.Image[itk.UC, 3]
    ReaderType = itk.ImageSeriesReader[ImageType]
    reader = ReaderType.New()
    reader.SetFileNames(filenames)
    reader.Update()

    image = reader.GetOutput()
    size_itk = image.GetLargestPossibleRegion().GetSize()
# %%
    PixelType = itk.SS  # signed short
    Dimension = 3
    ImageType = itk.Image[PixelType, Dimension]

    # GDCM IO and series name generator
# %%
    i=0
    io = itk.GDCMImageIO.New()
    io.SetFileName(str(dicom_files[0]))
    io.ReadImageInformation()
    uid = io.GetMetaDataDictionary().Get("0020|000e")  # SeriesInstanceUID
    metadata = io.GetMetaDataDictionary()
# %%

tagkeys = metadata.GetKeys()

for tagkey in tagkeys:
    # Note the [] operator for the key
    try:
        tagvalue = metadata[tagkey]
        print(tagkey + "=" + str(tagvalue))
    except RuntimeError:
        # Cannot pass specialized values into metadata dictionary.
        print("Cannot pass specialized value" + tagkey + "into metadadictionary")
# %%
    uid = itk.GDCMImageIO.GetAsciiStringFromMetaData("0020|000e",
                                                         io.GetMetaDataDictionary())
    uid = uid.strip()
# %%
    if uid:
            series_map.setdefault(uid, []).append(f)
# %%
    uid = io.GetMetaDataDictionary().Get("0020|000e")
    uid = itk.GDCMImageIO.GetAsciiStringFromMetaData("0020|000e",
                                                         io.GetMetaDataDictionary())
    name_gen = itk.GDCMSeriesFileNames.New()
    name_gen.SetUseSeriesDetails(True)
    name_gen.SetDirectory(str(dicom_dir))

# %%
    series_uids = name_gen.GetSeriesUIDs()
    if len(series_uids) == 0:
        raise RuntimeError(f"No DICOM series found in: {dicom_dir}")
# %%

    series_uid = series_uids[0]  # mirror C++: first series
    file_names = name_gen.GetFileNames(series_uid)
    if len(file_names) == 0:
        raise RuntimeError(f"No DICOM files for series {series_uid} in {dicom_dir}")

    # Reader
    ReaderType = itk.ImageSeriesReader[ImageType]
    reader = ReaderType.New()
    reader.SetImageIO(io)
    reader.SetFileNames(file_names)

    try:
        reader.Update()
    except RuntimeError as e:
        raise RuntimeError(f"ITK read error: {e}") from e

    image = reader.GetOutput()
    ReaderType = itk.ImageSeriesReader[itk.Image[itk.UC, 3]]
    r = ReaderType.New()
# %%
# %%
#SECTION:--------------------  per file--------------------------------------------------------------------------------------

    fn = dicom_files[0]
    fn = Path(fn)

    io = itk.GDCMImageIO.New()
    io.SetFileName(str(fn))

    io.ReadImageInformation()
    md = io.GetMetaDataDictionary()
    keys = md.GetKeys()
    tag =  "0020|0013"

    val = md[tag]
    str(val)
