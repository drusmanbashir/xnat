#include <filesystem>
#include <iostream>
#include <itkMacro.h>
#include <ostream>
#include <unordered_set>

#include <itkGDCMImageIO.h>
#include <itkGDCMSeriesFileNames.h>
#include <itkImageFileWriter.h>
#include <itkImageSeriesReader.h>
#include <itkNiftiImageIO.h>

namespace fs = std::filesystem;

bool is_dicom(const fs::directory_entry &e) {
  if (!e.is_regular_file())
    return false;
  auto ext = e.path().extension().string();
  std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
  return ext == ".dcm" || ext == ".dicom" || ext.empty();
}

int main() {
  // fs::path nodes_20 = "/path/to/root";
  //
  const std::string nodes_20 = "/media/UB/datasets/nodes/20/20/DICOM";
  using FileNamesGen = itk::GDCMSeriesFileNames;

  std::unordered_set<std::string> seen_folders;

  fs::recursive_directory_iterator it(
      nodes_20, fs::directory_options::follow_directory_symlink |
                    fs::directory_options::skip_permission_denied);

  for (const auto &dir_entry : it) {
    if (!is_dicom(dir_entry))
      continue;

    fs::path folder = dir_entry.path().parent_path();
    std::string folder_str = folder.string();

    // only process each folder once
    if (!seen_folders.insert(folder_str).second) {
      continue;
    }

    std::cout << "Folder: " << folder_str << '\n';

    auto nameGen = FileNamesGen::New();
    nameGen->SetUseSeriesDetails(true);
    nameGen->SetDirectory(folder_str);

    const auto &seriesUIDs = nameGen->GetSeriesUIDs();
    if (seriesUIDs.empty()) {
      std::cout << "  Not DICOM folder\n";
      continue;
    }

    // std::cout<<seriesUIDs.size()<<'\n';
    for (const auto &uid : seriesUIDs) {
      // std::cout << "  SeriesUID: " << uid << '\n';
      const itk::GDCMSeriesFileNames::FileNamesContainerType &filenames =
          nameGen->GetFileNames(uid);

      itk::ImageSeriesReader<itk::Image<short, 3>>::Pointer reader =
          itk::ImageSeriesReader<itk::Image<short, 3>>::New();
      reader->SetImageIO(itk::GDCMImageIO::New());
      reader->SetFileNames(filenames);
      try {
        reader->Update();
      } catch (itk::ExceptionObject &e) {
        std::cerr << " ITK read error for series " << uid << std::endl;
        std::cerr << "Folder : " << folder_str << std::endl;
        continue;
      }

      itk::Image<short, 3>::Pointer img = reader->GetOutput();
      const auto &size = img->GetLargestPossibleRegion().GetSize();
      std::cout << "Size : " << size << std::endl;

      auto writer = itk::ImageFileWriter<itk::Image<short, 3>>::New();
      auto const &out_filename = folder_str + ".nii.gz";
      writer->SetFileName(out_filename);
      writer->SetInput(img);
      writer->SetImageIO(itk::NiftiImageIO::New());
      try {
        writer->Update();
        std::cout << "Wrote " << out_filename << std::endl;

      } catch (itk::ExceptionObject &e) {
        std::cerr << " ITK write error for series " << uid << std::endl;
        std::cerr << "Folder : " << folder_str << std::endl;
        continue;
      }
    }
  }

  return 0;
}
