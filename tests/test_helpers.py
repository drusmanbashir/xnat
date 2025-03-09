import pytest
from pathlib import Path
from xnat.helpers import fn_to_attr, readable_text, fix_filename
import tempfile
import shutil

def test_fn_to_attr():
    # Test cases with expected outputs
    test_cases = [
        (
            "sub_001_20230615_T1w_thick.nii.gz",
            ("sub_001", "20230615", "T1w", "thick", ".nii.gz")
        ),
        (
            "control_123_20231001_flair_thick_processed.nii",
            ("control_123", "20231001", "flair", "thick", ".nii")
        ),
        (
            "pat_456_20220131_t2_thick.nrrd.gz",
            ("pat_456", "20220131", "t2", "thick", ".nrrd.gz")
        )
    ]
    
    for input_fname, expected in test_cases:
        result = fn_to_attr(Path(input_fname))
        assert result == expected, f"Failed for {input_fname}"

def test_readable_text():
    test_cases = [
        ("T1&T2", "T1T2"),
        ("pre/post", "prepost"),
        ("scan+contrast", "scancontrast"),
        ("scan.1", "scanp1"),
        ("scan 2", "scan2"),
        ("scan,3", "scan3"),
        ("scan(4)", "scan4"),
        ("scan_5", "scan5")
    ]
    
    for input_text, expected in test_cases:
        result = readable_text(input_text)
        assert result == expected, f"Failed for {input_text}"

def test_fix_filename():
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file
        test_path = Path(tmpdir) / "sub_001_20230615_T1_num_1_thick.nii.gz"
        test_path.touch()
        
        # Expected new filename
        expected_path = Path(tmpdir) / "sub_001_20230615_T1num1_thick.nii.gz"
        
        # Run fix_filename
        fix_filename(test_path)
        
        # Check if old file is gone and new file exists
        assert not test_path.exists(), "Old file should not exist"
        assert expected_path.exists(), "New file should exist"

def test_collate_nii_foldertree(tmp_path):
    from xnat.helpers import collate_nii_foldertree
    
    # Create source directory structure
    src_dir = tmp_path / "source"
    src_dir.mkdir()
    (src_dir / "subdir1").mkdir()
    (src_dir / "subdir2").mkdir()
    
    # Create some test files
    test_files = [
        "sub_001_20230615_T1w_thick.nii.gz",
        "subdir1/sub_002_20230615_T2w_thick.nii.gz",
        "subdir2/sub_003_20230615_flair_thick.nii.gz"
    ]
    
    for file_path in test_files:
        full_path = src_dir / file_path
        full_path.parent.mkdir(exist_ok=True)
        full_path.touch()
    
    # Create destination directory
    dest_dir = tmp_path / "destination"
    
    # Run the function
    collate_nii_foldertree(src_dir, dest_dir)
    
    # Check if all files are moved to destination
    for file_name in [Path(f).name for f in test_files]:
        assert (dest_dir / file_name).exists()
        
    # Check if source files are no longer in original location
    for file_path in test_files:
        assert not (src_dir / file_path).exists()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
