// dcm2nii_sanitized.h
#pragma once

#include <itkImage.h>
#include <itkImageSeriesReader.h>
#include <itkImageFileWriter.h>
#include <itkGDCMImageIO.h>
#include <itkNiftiImageIO.h>
#include <itkMetaDataObject.h>

#include <filesystem>
#include <unordered_map>
#include <vector>
#include <string>
#include <algorithm>
#include <stdexcept>
#include <iostream>

 

