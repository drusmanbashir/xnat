import setuptools
import os
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
with open(os.path.join(os.path.dirname(__file__), "requirements.txt"), encoding="utf-8") as f:
    requirements = f.read().splitlines()
setuptools.setup(
    name="xnat",  # Replace with your package name
    version="0.1.0",  # Update version as needed
    author="Usman Bashir",
    description="A Python package for interfacing with XNAT servers.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/xnat",  # Replace with your repo URL
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",  # Change if using another license
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=requirements
)
