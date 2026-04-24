#!/usr/bin/env python3

"""
Migrate OCI images from projects.packages.broadcom.com to a target software depot.

One positional action is required: download, upload, copy, or map-target-repo.
See --help for details and examples.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Reversed mappings (from legacy/projects format to FDS format)
REVERSE_MAPPINGS = [
    {
        "comment": "VCF CLI plugin inventory",
        "pattern": r"^/vcf-cli/plugins/plugin-inventory/(.+)$",
        "target": "/vcf-cli-plugins/ga/plugin-inventory/$1"
    },
    {
        "comment": "VCF CLI plugins",
        "pattern": r"^/vcf-cli/plugins/vmware/(.+)$",
        "target": "/vcf-cli-plugins/ga/vmware/$1"
    },
    {
        "comment": "VKR baker image",
        "pattern": r"^/vsphere/iaas/kubernetes-release/(.+)$",
        "target": "/vsphere-kubernetes-release/ga/$1"
    },
    {
        "comment": "VKS supervisor service",
        "pattern": r"^/vsphere/iaas/vsphere-kubernetes-service/(.+)$",
        "target": "/supervisor-service-vks/ga/$1"
    },
    {
        "comment": "VKS standard packages",
        "pattern": r"^/vsphere/supervisor/vks-standard-packages/(.+)$",
        "target": "/vks-standard-packages/ga/$1"
    },
    {
        "comment": "LCI supervisor service",
        "pattern": r"^/vsphere/iaas/lci-service/(.+)$",
        "target": "/supervisor-service-lci/ga/$1"
    },
    {
        "comment": "CA cluster issuer supervisor service",
        "pattern": r"^/vsphere/iaas/ca-clusterissuer/(.+)$",
        "target": "/supervisor-service-ca-clusterissuer/ga/$1"
    },
    {
        "comment": "Harbor supervisor service",
        "pattern": r"^/vsphere/supervisor/harbor-service/(.+)$",
        "target": "/supervisor-service-harbor/ga/$1"
    },
    {
        "comment": "Harbor VCF service",
        "pattern": r"^/vcf/services/harbor/(.+)$",
        "target": "/vcf-service-harbor/ga/$1"
    },
    {
        "comment": "Contour supervisor service",
        "pattern": r"^/vsphere/supervisor/contour/(.+)$",
        "target": "/supervisor-service-contour/ga/$1"
    },
    {
        "comment": "External DNS supervisor service",
        "pattern": r"^/vsphere/supervisor/external-dns/(.+)$",
        "target": "/supervisor-service-extdns/ga/$1"
    },
    {
        "comment": "Data consumption supervisor service images",
        "pattern": r"^/vsphere/supervisor/dsm-consumption-operator/([\d\.]+)/dsm-consumption-operator-supervisor:(.+)$",
        "target": "/vcf-service-data-services/ga/$1/dsm-consumption-operator-supervisor:$2"
    },
    {
        "comment": "Data consumption VCF service images",
        "pattern": r"^/vcf/services/data-services/([\d\.]+)/data-services:(.+)$",
        "target": "/vcf-service-data-services/ga/$1/data-services:$2"
    },
    {
        "comment": "Supervisor management proxy supervisor service",
        "pattern": r"^/vsphere/iaas/supervisor-management-proxy-service/(.+)$",
        "target": "/supervisor-service-supervisor-management-proxy/ga/$1"
    },
    {
        "comment": "Metrics aggregator supervisor service",
        "pattern": r"^/vsphere/iaas/metrics-aggregator/(.+)$",
        "target": "/supervisor-service-metrics-aggregator/ga/$1"
    },
    {
        "comment": "Metrics aggregator VCF service",
        "pattern": r"^/vcf/services/metrics-aggregator/(.+)$",
        "target": "/vcf-service-metrics-aggregator/ga/$1"
    },
    {
        "comment": "Argo CD supervisor service",
        "pattern": r"^/vsphere/supervisor/argocd-service/(.+)$",
        "target": "/vcf-service-argocd/ga/$1"
    },
    {
        "comment": "Secret store supervisor service",
        "pattern": r"^/vsphere/supervisor/vcf-service-secret-store/([\d\.]+)/secret-store-service:(.+)$",
        "target": "/vcf-service-secret-store/ga/$1/secret-store-service:$2"
    },
    {
        "comment": "Secret store VCF service",
        "pattern": r"^/vcf/services/vcf-service-secret-store/([\d\.]+)/vcf-service-secret-store:(.+)$",
        "target": "/vcf-service-secret-store/ga/$1/vcf-service-secret-store:$2"
    },
    {
        "comment": "Protection and recovery VCF service",
        "pattern": r"^/vcf/services/protection-and-recovery/(.+)$",
        "target": "/vcf-service-protection-and-recovery/ga/$1"
    },
    {
        "comment": "Protection and recovery supervisor service",
        "pattern": r"^/vsphere/supervisor/supervisor-service-dr-operator/(.+)$",
        "target": "/vcf-service-protection-and-recovery/ga/$1"
    },
    {
        "comment": "VKSM auto attach VCF service",
        "pattern": r"^/vcf/services/vksm-auto-attach/(.+)$",
        "target": "/vcf-service-vksm-auto-attach/ga/$1"
    },
    {
        "comment": "Configuration supervisor service",
        "pattern": r"^/vsphere/supervisor/configuration/([\d\.]+)/configuration-service:(.+)$",
        "target": "/vcf-service-configuration/ga/$1/configuration-service:$2"
    },
    {
        "comment": "Configuration VCF service",
        "pattern": r"^/vcf/services/configuration/([\d\.]+)/configuration:(.+)$",
        "target": "/vcf-service-configuration/ga/$1/configuration:$2"
    },
    {
        "comment": "Encryption management VCF service",
        "pattern": r"^/vcf/services/encryption-management/(.+)$",
        "target": "/vcf-service-encryption-management/ga/$1"
    },
    {
        "comment": "VCD migration VCF service",
        "pattern": r"^/vcf/services/migration/(.+)$",
        "target": "/vcf-service-migration/ga/$1"
    },
    {
        "comment": "VKSM extensions",
        "pattern": r"^/vsphere/vksm/extensions/(.+)$",
        "target": "/vksm-extensions/ga/$1"
    },
]

DEPOT_CA_FILENAME = "depot-ca.crt"


def apply_reverse_mapping(path: str) -> Optional[str]:
    for mapping in REVERSE_MAPPINGS:
        pattern = mapping["pattern"]
        target_template = mapping["target"]
        target = target_template.replace('$1', r'\1').replace('$2', r'\2').replace('$3', r'\3')
        match = re.match(pattern, path)
        if match:
            return re.sub(pattern, target, path)
    return None


def convert_repo_path(source_path: str, target_fqdn: str) -> str:
    parts = source_path.split('/', 1)
    if len(parts) < 2:
        return target_fqdn
    path_component = '/' + parts[1]
    converted_path = apply_reverse_mapping(path_component)
    if converted_path is None:
        print(f"Warning: No mapping rule found for path: {path_component}", file=sys.stderr)
        converted_path = path_component
    converted_path = converted_path.split(':')[0]
    return f"{target_fqdn}{converted_path}"


def tar_name_from_source(source_path: str) -> str:
    """Derive a safe .tar filename from the image reference (repo:tag tail)."""
    parts = source_path.split('/', 1)
    if len(parts) < 2:
        raise ValueError(f"Invalid source path (need domain/path): {source_path}")
    path_after_domain = parts[1]
    image_ref = path_after_domain.rsplit('/', 1)[-1]
    safe = re.sub(r'[^a-zA-Z0-9._-]+', '-', image_ref.replace(':', '-'))
    safe = safe.strip('-') or "image"
    return f"{safe}.tar"


def require_cmd(name: str) -> str:
    path = shutil.which(name)
    if not path:
        print(f"Error: '{name}' not found in PATH", file=sys.stderr)
        sys.exit(1)
    return path


def run_cmd(
    args: list[str],
    *,
    cwd: Optional[Path] = None,
    stdin_devnull: bool = True,
    step: str = "",
) -> None:
    print(f"+ {' '.join(args)}", file=sys.stderr)
    kwargs: dict = {}
    if stdin_devnull:
        kwargs["stdin"] = subprocess.DEVNULL
    r = subprocess.run(args, cwd=cwd, **kwargs)
    if r.returncode != 0:
        prefix = f"{step}: " if step else ""
        print(
            f"Error: {prefix}imgpkg (or subprocess) failed with exit code {r.returncode}.",
            file=sys.stderr,
        )
        sys.exit(r.returncode)


def fetch_depot_ca(fqdn: str, out_path: Path) -> None:
    """Write PEM certificate(s) from TLS server to out_path (awk range through first END)."""
    require_cmd("openssl")
    require_cmd("awk")
    print(
        f"+ openssl s_client -connect {fqdn}:443 -showcerts | awk '/BEGIN CERTIFICATE/,/END CERTIFICATE/' > {out_path}",
        file=sys.stderr,
    )
    p_ssl = subprocess.Popen(
        ["openssl", "s_client", "-connect", f"{fqdn}:443", "-showcerts"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        p_awk = subprocess.run(
            ["awk", "/BEGIN CERTIFICATE/,/END CERTIFICATE/"],
            stdin=p_ssl.stdout,
            stdout=subprocess.PIPE,
            check=False,
        )
    finally:
        if p_ssl.stdout:
            p_ssl.stdout.close()
        rc_ssl = p_ssl.wait()
    if rc_ssl not in (0, 1):
        print(
            f"Error fetching target depot TLS certificate: openssl s_client exited with code {rc_ssl}.",
            file=sys.stderr,
        )
        sys.exit(rc_ssl)
    if p_awk.returncode != 0:
        print(
            f"Error fetching target depot TLS certificate: awk exited with code {p_awk.returncode}.",
            file=sys.stderr,
        )
        sys.exit(p_awk.returncode)
    data = p_awk.stdout
    if not data or b"BEGIN CERTIFICATE" not in data:
        print(
            "Error fetching target depot TLS certificate: no PEM certificate extracted from the server.",
            file=sys.stderr,
        )
        sys.exit(1)
    out_path.write_bytes(data)


def _remove_temp_file(path: Path, description: str) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        print(
            f"Warning: upload succeeded but could not remove temporary {description} ({path}): {exc}",
            file=sys.stderr,
        )


def workflow_download_only(source_image_repo: str, work_dir: Path) -> None:
    """Download bundle to tar under work_dir; leave tar on disk."""
    require_cmd("imgpkg")

    tar_path = work_dir / tar_name_from_source(source_image_repo)

    print(
        "\noci_image_depot_migrator — download operation:\n"
        "  Download the image bundle from the source repository as a local tar file "
        "(imgpkg copy -b … --to-tar). The tar is kept after this command finishes.\n",
        file=sys.stderr,
    )
    print(f"  Source bundle:  {source_image_repo}", file=sys.stderr)
    print(f"  Work directory: {work_dir}", file=sys.stderr)
    print(f"  Output tar:       {tar_path}\n", file=sys.stderr)

    run_cmd(
        [
            "imgpkg",
            "copy",
            "-b",
            source_image_repo,
            "--to-tar",
            str(tar_path),
            "--cosign-signatures",
        ],
        cwd=work_dir,
        step="Download (imgpkg copy to tar)",
    )

    print(str(tar_path.resolve()))
    print("Done.", file=sys.stderr)


def workflow_upload_only(source_image_repo: str, target_depot_fqdn: str, work_dir: Path) -> None:
    """Upload an existing tar whose name matches tar_name_from_source(source_image_repo)."""
    tar_path = work_dir / tar_name_from_source(source_image_repo)
    ca_path = work_dir / DEPOT_CA_FILENAME
    target_repo = convert_repo_path(source_image_repo, target_depot_fqdn)

    if not tar_path.is_file():
        print(
            f"Error: upload requires a tar file at:\n  {tar_path}\n"
            "The filename must match the name produced by the same --source-image-repo with "
            "download operation or the full import download step (see tar naming rules in --help).",
            file=sys.stderr,
        )
        sys.exit(1)

    require_cmd("imgpkg")
    require_cmd("openssl")

    print(
        "\noci_image_depot_migrator — upload operation:\n"
        "  1) Use the existing local tar (must match the name derived from --source-image-repo).\n"
        "  2) Map the source repo path to the target depot repo URL (see below).\n"
        "  3) Fetch the target depot TLS certificate, then upload the tar with imgpkg.\n"
        "  4) Remove the temporary tar and certificate files after a successful upload.\n",
        file=sys.stderr,
    )
    print(f"  Source bundle (for path mapping & tar name): {source_image_repo}", file=sys.stderr)
    print(f"  Target depot FQDN: {target_depot_fqdn}", file=sys.stderr)
    print(f"  Target repo URL:   {target_repo}", file=sys.stderr)
    print(f"  Work directory:    {work_dir}", file=sys.stderr)
    print(f"  Tar file:          {tar_path}", file=sys.stderr)
    print(f"  Temporary CA file: {ca_path}\n", file=sys.stderr)

    print(
        "Step 2: Source repo path maps to the target repo URL above (used as --to-repo).",
        file=sys.stderr,
    )
    print("Step 3: Fetching target depot TLS certificate…", file=sys.stderr)
    fetch_depot_ca(target_depot_fqdn, ca_path)

    run_cmd(
        [
            "imgpkg",
            "copy",
            "--tar",
            str(tar_path),
            "--to-repo",
            target_repo,
            "--cosign-signatures",
            "--registry-ca-cert-path",
            str(ca_path),
        ],
        cwd=work_dir,
        step="Upload (imgpkg copy from tar to target repo)",
    )

    _remove_temp_file(tar_path, "tar file")
    _remove_temp_file(ca_path, "depot certificate file")

    print(target_repo)
    print("Done.", file=sys.stderr)


def workflow_copy(source_image_repo: str, target_depot_fqdn: str, work_dir: Path) -> None:
    require_cmd("imgpkg")
    require_cmd("openssl")

    tar_name = tar_name_from_source(source_image_repo)
    tar_path = work_dir / tar_name
    ca_path = work_dir / DEPOT_CA_FILENAME
    target_repo = convert_repo_path(source_image_repo, target_depot_fqdn)

    print(
        "\noci_image_depot_migrator — copy operation:\n"
        "  1) Download the image bundle from the source repository as a local tar file (imgpkg copy -b … --to-tar).\n"
        "  2) Map the source repo path to the target software depot repo path (see below); that URL is used for upload.\n"
        "  3) Fetch the target depot TLS certificate for registry trust (openssl), then write it beside the tar.\n"
        "  4) Upload the tar to the target repo (imgpkg copy --tar … --to-repo …), then delete the temporary tar "
        "and certificate files.\n",
        file=sys.stderr,
    )
    print(f"  Source bundle:     {source_image_repo}", file=sys.stderr)
    print(f"  Target depot FQDN: {target_depot_fqdn}", file=sys.stderr)
    print(f"  Target repo URL:   {target_repo}", file=sys.stderr)
    print(f"  Work directory:    {work_dir}", file=sys.stderr)
    print(f"  Temporary tar:     {tar_path}", file=sys.stderr)
    print(f"  Temporary CA file: {ca_path}\n", file=sys.stderr)

    run_cmd(
        [
            "imgpkg",
            "copy",
            "-b",
            source_image_repo,
            "--to-tar",
            str(tar_path),
            "--cosign-signatures",
        ],
        cwd=work_dir,
        step="Step 1 (download bundle from source repo to tar via imgpkg)",
    )

    print(
        "Step 2: Source repo path is mapped to the target repo URL shown above (used as --to-repo).",
        file=sys.stderr,
    )
    print("Step 3: Fetching target depot TLS certificate…", file=sys.stderr)
    fetch_depot_ca(target_depot_fqdn, ca_path)

    run_cmd(
        [
            "imgpkg",
            "copy",
            "--tar",
            str(tar_path),
            "--to-repo",
            target_repo,
            "--cosign-signatures",
            "--registry-ca-cert-path",
            str(ca_path),
        ],
        cwd=work_dir,
        step="Step 4 (upload tar to target repo via imgpkg)",
    )

    _remove_temp_file(tar_path, "tar file")
    _remove_temp_file(ca_path, "depot certificate file")

    print(target_repo)
    print("Done.", file=sys.stderr)


def main() -> None:
    epilog = """\
Actions:
  download          Download OCI tars to local --work-dir.
                    Uses imgpkg copy -b <REPO> --to-tar <derived>.tar.
                    Requires -s. -t is not required. The tar is kept on disk.

  upload            Upload an existing OCI tar to the target depot.
                    Expects a tar under --work-dir whose name matches the one
                    that download would produce for the same -s argument.
                    Requires -s and -t. Tar and depot CA are deleted on success.

  copy              Copy OCI images from source repo to target depot.
                    Does download + upload in one run and expects connectivity to both source and target.
                    Requires -s and -t. Temporary tar and depot CA are deleted on success.

  map-target-repo   Print the target Software Depot repo URL for a given OCI image (no tag).
                    Pure path conversion; does not run imgpkg to download or upload.
                    Requires -s and -t.

Tar naming:
  Basename is derived from the last segment of the source reference.
  ':' and unsafe characters are normalized.
  Example: .../argocd-service:v1.1.0_vmware.1 -> argocd-service-v1.1.0_vmware.1.tar

Examples:
  %(prog)s copy \\
      -s 'projects.packages.broadcom.com/.../argocd-service:v1.1.0_vmware.1' \\
      -t 'fleet-10-144-79-70.vcfd.broadcom.net'

  %(prog)s download \\
      -s 'projects.packages.broadcom.com/.../image:tag'

  %(prog)s upload \\
      -s 'projects.packages.broadcom.com/.../image:tag' \\
      -t 'fleet-10-144-79-70.vcfd.broadcom.net'

  %(prog)s map-target-repo \\
      -s 'projects.packages.broadcom.com/.../image:tag' \\
      -t 'fleet-10-144-79-70.vcfd.broadcom.net'
"""
    description = (
        "Migrate OCI images from projects.packages.broadcom.com to a target Software Depot.\n"
        "\n"
        "Action is a required positional argument:\n"
        "  download | upload | copy | map-target-repo\n"
        "\n"
        "Common options:\n"
        "  -s / --source-image-repo  REPO   always required\n"
        "  -t / --target-depot-fqdn  FQDN   required for upload, copy, map-target-repo\n"
        "  --work-dir DIR                   where tars and depot-ca.crt live (default: cwd)"
    )

    parser = argparse.ArgumentParser(
        prog="oci_image_depot_migrator.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=description,
        epilog=epilog,
    )
    parser.add_argument(
        "action",
        choices=["download", "upload", "copy", "map-target-repo"],
        metavar="ACTION",
        help="download | upload | copy | map-target-repo (see examples below).",
    )
    parser.add_argument(
        "-s",
        "--source-image-repo",
        required=True,
        metavar="REPO",
        help="Source bundle reference, e.g. projects.packages.broadcom.com/.../image:tag",
    )
    parser.add_argument(
        "-t",
        "--target-depot-fqdn",
        default=None,
        metavar="FQDN",
        help="Target Software Depot FQDN. Required for upload, copy, and map-target-repo.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory for .tar, depot-ca.crt, and imgpkg cwd. Default: current working directory.",
    )

    args = parser.parse_args()
    action = args.action

    if action == "download":
        if args.target_depot_fqdn is not None:
            print(
                "Note: -t/--target-depot-fqdn is ignored for action 'download'.",
                file=sys.stderr,
            )
    elif args.target_depot_fqdn is None:
        parser.error(
            f"action '{action}' requires -t/--target-depot-fqdn."
        )

    if action == "map-target-repo":
        print(convert_repo_path(args.source_image_repo, args.target_depot_fqdn))
        return

    args.work_dir.mkdir(parents=True, exist_ok=True)
    work = args.work_dir.resolve()

    if action == "download":
        workflow_download_only(args.source_image_repo, work)
    elif action == "upload":
        workflow_upload_only(args.source_image_repo, args.target_depot_fqdn, work)
    elif action == "copy":
        workflow_copy(args.source_image_repo, args.target_depot_fqdn, work)


if __name__ == "__main__":
    main()
