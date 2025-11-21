cmake_minimum_required(VERSION 3.25)

project(xnat_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(ITK REQUIRED COMPONENTS
    ITKCommon
    ITKIOGDCM
    ITKIONIFTI
    ITKIOImageBase
)
# Either use ITK_USE_FILE OR explicit imported targets. I'll show explicit.
# include(${ITK_USE_FILE})

find_package(pybind11 REQUIRED)

# 1) pybind11 module
add_library(xnat_cpp MODULE
    src/dcm2nii.cxx
)

target_link_libraries(xnat_cpp
    PRIVATE
        ITKCommon
        ITKIOGDCM
        ITKIONIFTI
        ITKIOImageBase
        pybind11::module
)

# Importable as "import xnat_cpp"
set_target_properties(xnat_cpp PROPERTIES
    PREFIX ""
)

# 2) demo executable
add_executable(xnat_cpp_demo
    src/main.cpp
)

target_link_libraries(xnat_cpp_demo
    PRIVATE
        ITKCommon
        ITKIOGDCM
        ITKIONIFTI
        ITKIOImageBase
)

# If you need your own headers:
target_include_directories(xnat_cpp_demo
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# No need to downgrade the standard here; project is already C++20
# target_compile_features(xnat_cpp_demo PRIVATE cxx_std_20)  # optional

