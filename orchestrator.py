#!/usr/bin/env python3
"""
VRL validate-deploy loop orchestrator.

Features:
- Writes a candidate VRL into `vector_config/parser.vrl`.
- Validates Vector YAML+VRL inside Docker using `vector validate`.
- Supports local Docker or remote EC2 host via SSH.
- On failure, shows errors and allows iterative edits until it passes.

Usage examples:
  Local validate with inline VRL text:
    python orchestrator.py --mode local --vrl "if exists(.message) { .event_data = .message }"

  Local validate using a VRL file:
    python orchestrator.py --mode local --vrl-file /path/to/parser.vrl

  Remote (EC2) validate:
    python orchestrator.py --mode remote \
      --ssh-host ec2-1-2-3-4.compute.amazonaws.com \
      --ssh-user ubuntu \
      --ssh-key /path/to/key.pem \
      --remote-workdir /home/ubuntu/dpm_testing \
      --vrl-file ./vector_config/parser.vrl

Notes:
- The script runs `docker compose -f docker-compose-test.yaml run --rm --entrypoint vector parser-package validate --config /etc/vector/config/config.yaml` to validate.
- It does not auto-run the full pipeline unless you pass --run-after-validate.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

try:
    import paramiko  # type: ignore
except Exception:
    paramiko = None  # Optional dependency for remote mode


REPO_ROOT = Path(__file__).resolve().parent
COMPOSE_FILE = REPO_ROOT / "docker-compose-test.yaml"
VRL_PATH = REPO_ROOT / "vector_config" / "parser.vrl"


def write_vrl_to_repo(vrl_text: str) -> None:
    VRL_PATH.parent.mkdir(parents=True, exist_ok=True)
    VRL_PATH.write_text(vrl_text, encoding="utf-8")


def read_text_file(file_path: Path) -> str:
    return Path(file_path).read_text(encoding="utf-8")


def _run_local(cmd: str) -> Tuple[int, str, str]:
    process = subprocess.Popen(
        cmd, shell=True, cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out_b, err_b = process.communicate()
    return process.returncode, out_b.decode("utf-8", "replace"), err_b.decode("utf-8", "replace")


def _ensure_paramiko():
    if paramiko is None:
        raise RuntimeError(
            "Remote mode requires paramiko. Install dependencies: pip install -r requirements.txt"
        )


def _run_remote(
    host: str,
    user: str,
    key_path: str,
    remote_workdir: str,
    cmd: str,
) -> Tuple[int, str, str]:
    _ensure_paramiko()
    key = paramiko.RSAKey.from_private_key_file(key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=user, pkey=key)
    try:
        full_cmd = f"cd {shlex.quote(remote_workdir)} && {cmd}"
        stdin, stdout, stderr = client.exec_command(full_cmd)
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
        return exit_status, out, err
    finally:
        client.close()


def build_image_local() -> None:
    cmd = f"docker compose -f {shlex.quote(str(COMPOSE_FILE))} build"
    code, out, err = _run_local(cmd)
    if code != 0:
        print(out)
        print(err, file=sys.stderr)
        raise RuntimeError("Docker build failed. See logs above.")


def validate_local() -> Tuple[bool, str]:
    cmd = (
        f"docker compose -f {shlex.quote(str(COMPOSE_FILE))} run --rm "
        f"--entrypoint vector parser-package validate --config /etc/vector/config/config.yaml"
    )
    code, out, err = _run_local(cmd)
    success = code == 0
    logs = (out + "\n" + err).strip()
    return success, logs


def run_pipeline_local(detach: bool) -> None:
    base = f"docker compose -f {shlex.quote(str(COMPOSE_FILE))} up --build"
    cmd = base + (" -d" if detach else "")
    code, out, err = _run_local(cmd)
    print(out)
    if code != 0:
        print(err, file=sys.stderr)
        raise RuntimeError("Failed to start pipeline.")


def build_image_remote(host: str, user: str, key: str, workdir: str) -> None:
    cmd = f"docker compose -f {shlex.quote(str(COMPOSE_FILE.name))} build"
    code, out, err = _run_remote(host, user, key, workdir, cmd)
    if code != 0:
        print(out)
        print(err, file=sys.stderr)
        raise RuntimeError("Remote docker build failed.")


def validate_remote(host: str, user: str, key: str, workdir: str) -> Tuple[bool, str]:
    cmd = (
        f"docker compose -f {shlex.quote(str(COMPOSE_FILE.name))} run --rm "
        f"--entrypoint vector parser-package validate --config /etc/vector/config/config.yaml"
    )
    code, out, err = _run_remote(host, user, key, workdir, cmd)
    success = code == 0
    logs = (out + "\n" + err).strip()
    return success, logs


def run_pipeline_remote(host: str, user: str, key: str, workdir: str, detach: bool) -> None:
    base = f"docker compose -f {shlex.quote(str(COMPOSE_FILE.name))} up --build"
    cmd = base + (" -d" if detach else "")
    code, out, err = _run_remote(host, user, key, workdir, cmd)
    print(out)
    if code != 0:
        print(err, file=sys.stderr)
        raise RuntimeError("Failed to start remote pipeline.")


def main() -> None:
    parser = argparse.ArgumentParser(description="VRL validate-deploy loop orchestrator")
    parser.add_argument("--mode", choices=["local", "remote"], required=True)
    parser.add_argument("--vrl", help="Inline VRL string to write into parser.vrl")
    parser.add_argument("--vrl-file", help="Path to a VRL file to copy into parser.vrl")
    parser.add_argument("--run-after-validate", action="store_true", help="Start pipeline if validate succeeds")
    parser.add_argument("--detach", action="store_true", help="Detach when starting the pipeline")

    # Remote options
    parser.add_argument("--ssh-host", help="Remote host (EC2 public DNS/IP)")
    parser.add_argument("--ssh-user", help="SSH username, e.g., ubuntu")
    parser.add_argument("--ssh-key", help="Path to private key .pem")
    parser.add_argument(
        "--remote-workdir",
        help="Path to repo directory on remote host containing docker-compose-test.yaml",
    )

    args = parser.parse_args()

    if not COMPOSE_FILE.exists():
        raise SystemExit(f"Compose file not found: {COMPOSE_FILE}")

    if args.vrl and args.vrl_file:
        raise SystemExit("Provide only one of --vrl or --vrl-file")
    if not args.vrl and not args.vrl_file:
        raise SystemExit("Provide --vrl or --vrl-file")

    if args.vrl:
        write_vrl_to_repo(args.vrl)
    else:
        vrl_text = read_text_file(Path(args.vrl_file))
        write_vrl_to_repo(vrl_text)

    if args.mode == "local":
        print("Building image locally...")
        build_image_local()
        print("Validating configuration in container...")
        ok, logs = validate_local()
        print(logs)
        if not ok:
            print("Validation failed. Edit vector_config/parser.vrl and re-run.", file=sys.stderr)
            sys.exit(2)
        print("Validation passed.")
        if args.run_after_validate:
            print("Starting pipeline...")
            run_pipeline_local(detach=args.detach)
    else:
        if not all([args.ssh_host, args.ssh_user, args.ssh_key, args.remote_workdir]):
            raise SystemExit("Remote mode requires --ssh-host, --ssh-user, --ssh-key, --remote-workdir")
        if paramiko is None:
            raise SystemExit("Install paramiko for remote mode: pip install -r requirements.txt")
        print("Building image on remote host...")
        build_image_remote(args.ssh_host, args.ssh_user, args.ssh_key, args.remote_workdir)
        print("Validating configuration on remote host...")
        ok, logs = validate_remote(args.ssh_host, args.ssh_user, args.ssh_key, args.remote_workdir)
        print(logs)
        if not ok:
            print("Validation failed on remote. Edit VRL and re-run.", file=sys.stderr)
            sys.exit(2)
        print("Validation passed on remote.")
        if args.run_after_validate:
            print("Starting pipeline on remote host...")
            run_pipeline_remote(args.ssh_host, args.ssh_user, args.ssh_key, args.remote_workdir, detach=args.detach)


if __name__ == "__main__":
    main()


