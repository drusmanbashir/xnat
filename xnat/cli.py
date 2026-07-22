from __future__ import annotations

import argparse
from pathlib import Path

from .object_oriented import Proj, Subj


def _input_with_default(prompt: str, default: str) -> str:
    raw = input(f"{prompt} [{default}]: ").strip()
    return raw or default


def download_project_resources(project_id: str, dest_folder: Path, label: str = "IMAGE") -> dict[str, int | str]:
    if not project_id.strip():
        raise ValueError("project_id cannot be empty")

    dest = Path(dest_folder).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    proj = Proj(project_id)
    subs = list(proj.subs)

    resources_matched = 0
    for sub_res in subs:
        sub = Subj(sub_res)
        matches = [rsc for rsc in sub.rscs if rsc.label() == label]
        resources_matched += len(matches)
        if matches:
            sub.download_rscs(label, str(dest))

    return {
        "project_id": project_id,
        "label": label,
        "dest_folder": str(dest),
        "subjects_scanned": len(subs),
        "resources_matched": resources_matched,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="xnat-cli", description="XNAT utility commands")
    sub = p.add_subparsers(dest="cmd", required=True)

    dln = sub.add_parser(
        "download-nifti",
        help="Download all resources with label IMAGE (or custom label) from a project",
    )
    dln.add_argument("--project", default="", help="XNAT project name")
    dln.add_argument("--dest", default="", help="Destination folder for downloaded files")
    dln.add_argument("--label", default="IMAGE", help="Resource label to download (default: IMAGE)")
    dln.add_argument("--no-ask", action="store_true", help="Do not prompt interactively")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd != "download-nifti":
        return 1

    project = args.project
    dest = args.dest
    label = args.label

    if not args.no_ask:
        project = _input_with_default("XNAT project name", project or "")
        dest = _input_with_default("Destination folder", dest or "/tmp/xnat_downloads")
        label = _input_with_default("Resource label", label or "IMAGE")

    if not project.strip():
        raise ValueError("Project name is required")
    if not dest.strip():
        raise ValueError("Destination folder is required")

    result = download_project_resources(project_id=project, dest_folder=Path(dest), label=label)
    print(f"project_id: {result['project_id']}")
    print(f"label: {result['label']}")
    print(f"dest_folder: {result['dest_folder']}")
    print(f"subjects_scanned: {result['subjects_scanned']}")
    print(f"resources_matched: {result['resources_matched']}")
    print("download complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
