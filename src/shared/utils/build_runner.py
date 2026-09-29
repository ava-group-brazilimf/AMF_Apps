#!/usr/bin/env python3
"""
build_runner.py — Docker/Podman build runner utilities for ava-stack-build-validator.

Provides helpers for running build commands inside Docker or Podman containers:
  - Path normalization (host → container-compatible volume paths)
  - Image name resolution by stack and version
  - Cache volume name generation
  - Platform flag detection
  - Node version extraction from existing Dockerfiles

Usage:
    python src/shared/utils/build_runner.py --normalize-path "C:\\path\\to\\project"
    python src/shared/utils/build_runner.py --normalize-path "C:\\path\\to\\project" --runtime podman
    python src/shared/utils/build_runner.py --image dotnet 10.0
    python src/shared/utils/build_runner.py --image node 20
    python src/shared/utils/build_runner.py --image angular 17 --node-version 20
    python src/shared/utils/build_runner.py --volumes backend Meu-ERP
    python src/shared/utils/build_runner.py --volumes frontend Meu-ERP
    python src/shared/utils/build_runner.py --read-node-version path/to/Dockerfile.frontend
    python src/shared/utils/build_runner.py --platform
    python src/shared/utils/build_runner.py --podman-socket

Exit codes:
    0 — success (ou service_running=true para --podman-socket)
    1 — error (unknown framework, invalid args, etc.; ou service_running=false para --podman-socket)

Notes:
    --normalize-path --runtime podman:
        On Windows hosts running inside Git Bash / MSYS2 (MSYSTEM env var set),
        Podman expects native Windows paths (C:/path/to/dir) rather than the
        MSYS2 double-slash format (//c/path/to/dir) used by Docker Desktop.
        Pass --runtime podman to get the correct format automatically.

    --image for frontend frameworks:
        The frontend framework version (e.g. Angular 17) is NOT the Node.js version.
        Always resolve node_version from tobe_stack.node_version in project-config.yaml
        and pass it via --node-version. Example:
            --image angular 17 --node-version 20  →  node:20-alpine
        Without --node-version, the framework version is used and a warning is emitted.
"""

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


# ─── Image Resolution ─────────────────────────────────────────────────────────

# Maps framework name → Docker image template (build/SDK stage only).
# Runtime images (aspnet, nginx) are not used for build validation.
BACKEND_IMAGES = {
    "dotnet":      "mcr.microsoft.com/dotnet/sdk:{version}",
    "spring-boot": "eclipse-temurin:{version}-jdk-alpine",
    "fastapi":     "python:{version}-slim",
    "gin":         "golang:{version}-alpine",
    "nestjs":      "node:{version}-alpine",
}

FRONTEND_IMAGES = {
    "angular": "node:{version}-alpine",
    "react":   "node:{version}-alpine",
    "vue":     "node:{version}-alpine",
    "svelte":  "node:{version}-alpine",
    "blazor":  "mcr.microsoft.com/dotnet/sdk:{version}",
}


# Frontend frameworks whose image is Node-based (version = Node version, NOT framework version)
_FRONTEND_NODE_FRAMEWORKS = frozenset(FRONTEND_IMAGES.keys()) - {"blazor"}


def resolve_image(framework: str, version: str, node_version: str = "") -> str:
    """Return the Docker image reference for a given framework and version.

    For Node-based frontend frameworks (angular, react, vue, svelte) the *version*
    argument is expected to be the **Node.js** major version, NOT the framework
    version.  Pass ``node_version`` explicitly when the caller holds a framework
    version (e.g. Angular 17) separately from the Node version (e.g. 20); this
    function will then use ``node_version`` and emit a warning when the two values
    differ so the agent is alerted to a potential misconfiguration.

    Args:
        framework:    Stack identifier (e.g., "dotnet", "node", "angular").
        version:      Version string.  For backend stacks: SDK/runtime version
                      (e.g. "10.0").  For Node-based frontends: should be the
                      Node.js version — use ``node_version`` instead when you have
                      the framework version only.
        node_version: When non-empty and *framework* is a Node-based frontend,
                      this overrides *version* as the Node.js image tag.  The
                      caller should always pass this from
                      ``tobe_stack.node_version`` in project-config.yaml.

    Returns:
        Fully qualified Docker image reference (e.g., "node:20-alpine").
    """
    # Allow "node" as a shorthand for any Node-based frontend
    if framework == "node":
        effective = node_version if node_version else version
        return f"node:{effective}-alpine"

    template = BACKEND_IMAGES.get(framework) or FRONTEND_IMAGES.get(framework)
    if not template:
        print(f"ERROR: Unknown framework '{framework}'.", file=sys.stderr)
        print(
            f"Known backends : {', '.join(BACKEND_IMAGES.keys())}",
            file=sys.stderr,
        )
        print(
            f"Known frontends: {', '.join(FRONTEND_IMAGES.keys())}",
            file=sys.stderr,
        )
        sys.exit(1)

    # For Node-based frontend frameworks: the Docker image tag is the Node.js version,
    # not the framework version.  Warn loudly when node_version is absent so that
    # callers that accidentally pass the framework version (e.g. "17" for Angular 17)
    # are alerted before they silently pull a wrong / EOL Node image.
    if framework in _FRONTEND_NODE_FRAMEWORKS:
        if node_version:
            if node_version != version:
                print(
                    f"WARNING: --image {framework} {version} overridden by "
                    f"--node-version {node_version}. "
                    f"Node image will be node:{node_version}-alpine "
                    f"(framework version '{version}' is NOT the Node version).",
                    file=sys.stderr,
                )
            return template.replace("{version}", node_version)
        else:
            print(
                f"WARNING: --image {framework} {version} — '{version}' is being used "
                f"as the Node.js image tag, but this may be the framework version, not "
                f"the Node.js version.  Resolve tobe_stack.node_version from "
                f"project-config.yaml and pass it via --node-version to avoid pulling "
                f"the wrong Node image (e.g. node:{version}-alpine when Node {version} "
                f"may be EOL).  Recommended: --image node {{node_version}}.",
                file=sys.stderr,
            )

    return template.replace("{version}", version)


# ─── Path Normalization ────────────────────────────────────────────────────────

def normalize_path_for_docker(path: str, runtime: str = "docker") -> str:
    """
    Normalize a host filesystem path to a container-compatible volume mount path.

    Docker Desktop on Windows (WSL2 backend) accepts volume paths in POSIX
    format with a double-slash drive prefix:
        C:\\path\\to\\project  →  //c/path/to/project

    Podman on Windows, however, requires a **native Windows path** (forward
    slashes) when called from Git Bash / MSYS2, because the MSYS2 runtime
    mis-interprets the double-slash prefix as a UNC path:
        C:\\path\\to\\project  →  C:/path/to/project

    This function detects the MSYS2 environment (MSYSTEM or MINGW_PREFIX env
    vars) and, when runtime="podman", returns the Windows-native format so
    that callers do NOT need to prefix every `podman run` command with
    `MSYS_NO_PATHCONV=1`.

    On Linux and macOS, absolute paths are returned unchanged regardless of
    the runtime argument.

    Args:
        path:    Absolute or relative path on the host filesystem.
        runtime: "docker" (default) or "podman". Controls path format on
                 Windows + MSYS2 hosts.

    Returns:
        Container-compatible path string suitable for use in `-v` flag.
    """
    p = Path(path).resolve()

    if platform.system() == "Windows":
        drive = p.drive          # e.g. "C:"
        if drive:
            drive_letter = drive[0].lower()          # "c"
            rest = str(p)[len(drive):]               # "\\path\\to\\dir"
            rest_posix = rest.replace("\\", "/")     # "/path/to/dir"

            # Podman on Windows + Git Bash / MSYS2: return native Windows path
            # (C:/path/to/dir) to avoid MSYS2 double-slash UNC mis-interpretation.
            # The MSYS2 environment is present when MSYSTEM (e.g. "MINGW64") or
            # MINGW_PREFIX is set — both are standard in Git for Windows.
            is_msys2 = bool(
                os.environ.get("MSYSTEM") or os.environ.get("MINGW_PREFIX")
            )
            if runtime == "podman" and is_msys2:
                return f"{drive_letter.upper()}:{rest_posix}"

            # Docker Desktop (WSL2 backend) + default: POSIX double-slash format
            return f"//{drive_letter}{rest_posix}"

    # Linux / macOS — POSIX path as-is
    return str(p)


# ─── Cache Volume Names ────────────────────────────────────────────────────────

def get_volume_flags(target: str, project_name: str) -> list[str]:
    """
    Return the list of Docker -v flags for cache volumes.

    Backend (.NET):
        -v ava-nuget-{project}:/root/.nuget/packages

    Frontend (JS/TS):
        -v ava-node-modules-{project}:/workspace/node_modules
        -v ava-npm-cache-{project}:/root/.npm

    Node modules are stored in a named volume (not a bind-mount) to avoid
    Windows/macOS filesystem performance issues and permission conflicts.
    The bind-mounted workspace still reflects fixer edits (package.json etc.)
    so the next npm ci in the container picks up changes immediately.

    Args:
        target: "backend" or "frontend"
        project_name: project identifier (spaces replaced with hyphens)

    Returns:
        List of -v flag strings.
    """
    safe_name = project_name.replace(" ", "-").lower()

    if target == "backend":
        return [f"-v ava-nuget-{safe_name}:/root/.nuget/packages"]

    if target == "frontend":
        return [
            f"-v ava-node-modules-{safe_name}:/workspace/node_modules",
            f"-v ava-npm-cache-{safe_name}:/root/.npm",
        ]

    print(
        f"ERROR: Unknown target '{target}'. Use 'backend' or 'frontend'.",
        file=sys.stderr,
    )
    sys.exit(1)


# ─── Node Version Extraction from Dockerfile ──────────────────────────────────

# Default Node LTS version when no other source is available
NODE_LTS_DEFAULT = "22"


def read_node_version_from_dockerfile(dockerfile_path: str) -> str:
    """
    Extract the Node.js major version from an existing Dockerfile.

    Searches for patterns such as:
        FROM node:20-alpine
        FROM node:22-alpine3.21
        FROM node:20.19.0-slim

    Returns the major version string (e.g., "20") or NODE_LTS_DEFAULT if
    the Dockerfile does not exist or contains no matching FROM instruction.

    Args:
        dockerfile_path: Path to a Dockerfile (e.g., "Dockerfile.frontend").

    Returns:
        Node.js major version string.
    """
    try:
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        match = re.search(r"FROM\s+node:(\d+)", content, re.IGNORECASE)
        if match:
            return match.group(1)

    except (FileNotFoundError, OSError):
        pass

    return NODE_LTS_DEFAULT


# ─── Platform Detection ────────────────────────────────────────────────────────

def detect_platform_flag() -> str:
    """
    Return the --platform flag for Docker when running on an ARM host.

    Apple M1/M2/M3 (arm64) hosts should pull linux/amd64 images by default
    to avoid running experimental ARM builds of SDK images. Setting this flag
    explicitly requests x86_64 emulation via Rosetta 2 / QEMU.

    Returns:
        "--platform linux/amd64" on ARM hosts, empty string on x86_64.
    """
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "--platform linux/amd64"
    return ""


# ─── Container Runtime Detection ─────────────────────────────────────────────

def detect_runtime(preferred: str = "auto") -> str:
    """
    Detect available container runtime on the host.

    Checks PATH for `docker` and/or `podman` executables.
    In "auto" mode, Docker takes precedence over Podman when both are present.
    Podman is a drop-in replacement for Docker (same CLI syntax, OCI-compliant
    images) and requires no daemon on Linux.

    Args:
        preferred: "docker" | "podman" | "auto"

    Returns:
        "docker", "podman", or "none"
    """
    has_docker = shutil.which("docker") is not None
    has_podman = shutil.which("podman") is not None

    if preferred == "docker":
        return "docker" if has_docker else "none"

    if preferred == "podman":
        return "podman" if has_podman else "none"

    # "auto" — docker takes precedence when both are present
    if has_docker:
        return "docker"
    if has_podman:
        return "podman"
    return "none"


def get_runtime_info(runtime: str) -> dict:
    """
    Check if a container runtime is available and its service is responding.

    Docker requires a running daemon (dockerd). Podman is daemonless on Linux
    and responds to `podman info` without a background service. On Windows and
    macOS, Podman requires a running podman machine VM — `podman info` fails
    if the VM is not started, giving the same failure signature as Docker.

    Args:
        runtime: "docker" or "podman"

    Returns:
        dict with keys:
            runtime         — echoes input
            version         — "X.Y.Z" extracted from `{runtime} --version`
            available       — True if binary found in PATH
            service_running — True if `{runtime} info` exits 0
            method          — command used for service check
            error           — error message if any step failed, else ""
    """
    result: dict = {
        "runtime": runtime,
        "version": "",
        "available": False,
        "service_running": False,
        "method": f"{runtime} info",
        "error": "",
    }

    if shutil.which(runtime) is None:
        result["error"] = f"{runtime} not found in PATH"
        return result

    result["available"] = True

    # Extract version string
    try:
        ver_proc = subprocess.run(
            [runtime, "--version"],
            capture_output=True, text=True, timeout=10,
        )
        ver_output = ver_proc.stdout.strip() or ver_proc.stderr.strip()
        m = re.search(r"(\d+\.\d+\.\d+)", ver_output)
        result["version"] = m.group(1) if m else ver_output
    except (subprocess.TimeoutExpired, OSError) as exc:
        result["error"] = str(exc)
        return result

    # Check service / machine health
    try:
        info_proc = subprocess.run(
            [runtime, "info"],
            capture_output=True, text=True, timeout=15,
        )
        result["service_running"] = info_proc.returncode == 0
        if not result["service_running"]:
            stderr = info_proc.stderr.strip()
            result["error"] = stderr.split("\n")[0] if stderr else "service check failed"
    except (subprocess.TimeoutExpired, OSError) as exc:
        result["service_running"] = False
        result["error"] = str(exc)

    return result


# ─── Podman Socket Detection ─────────────────────────────────────────────────

def get_podman_socket_info() -> dict:
    """
    Detecta o socket Podman disponível no host atual e retorna as informações
    necessárias para configurar o Testcontainers .NET.

    Estratégia de detecção:
    1. Verificar se o binário `podman` existe em PATH
    2. Detectar OS (Linux / macOS / Windows)
    3. No Linux:
       a. Verificar se o processo roda como root (uid == 0)
       b. Rootless: socket = /run/user/{uid}/podman/podman.sock
       c. Rootful:  socket = /run/podman/podman.sock
       d. Verificar existência do arquivo de socket (os.path.exists)
       e. Verificar se `podman info` responde com exit 0
    4. No macOS/Windows:
       a. Executar `podman machine list --format json` para listar machines
       b. Localizar a machine com Running=true
       c. Executar `podman machine inspect {name}` para obter o socket path
       d. Extrair ConnectionInfo.PodmanSocket.Path ou ConnectionInfo.URI
    5. Se DOCKER_HOST env var já estiver definida: registrar como hint (não substituir)

    Returns:
        dict com chaves: available, socket_path, docker_host_uri, rootless,
        service_running, ryuk_disabled, platform, machine_name, error,
        docker_host_already_set.
    """
    result: dict = {
        "available": False,
        "socket_path": "",
        "docker_host_uri": "",
        "rootless": False,
        "service_running": False,
        "ryuk_disabled": False,
        "platform": platform.system().lower(),
        "machine_name": "",
        "error": "",
        "docker_host_already_set": bool(os.environ.get("DOCKER_HOST")),
    }

    if shutil.which("podman") is None:
        result["error"] = "podman not found in PATH"
        return result

    result["available"] = True
    current_platform = platform.system()

    if current_platform == "Linux":
        try:
            uid = os.getuid()
        except AttributeError:
            uid = 0
        is_root = (uid == 0)
        socket_path = "/run/podman/podman.sock" if is_root else f"/run/user/{uid}/podman/podman.sock"
        rootless = not is_root

        socket_exists = os.path.exists(socket_path)
        service_running = False
        try:
            proc = subprocess.run(
                ["podman", "info"],
                capture_output=True, text=True, timeout=10,
            )
            service_running = socket_exists and (proc.returncode == 0)
            if not service_running and proc.returncode != 0:
                stderr = proc.stderr.strip()
                result["error"] = stderr.split("\n")[0] if stderr else "podman info failed"
        except (subprocess.TimeoutExpired, OSError) as exc:
            result["error"] = str(exc)

        if not socket_exists and not result["error"]:
            result["error"] = f"socket file not found: {socket_path}"

        result.update({
            "socket_path": socket_path,
            "docker_host_uri": f"unix://{socket_path}",
            "rootless": rootless,
            "service_running": service_running,
            "ryuk_disabled": rootless,  # recomendado apenas para rootless no Linux
        })

    else:  # macOS / Windows
        try:
            proc = subprocess.run(
                ["podman", "machine", "list", "--format", "json"],
                capture_output=True, text=True, timeout=15,
            )
            if proc.returncode != 0:
                result["error"] = proc.stderr.strip() or "podman machine list failed"
                return result

            machines = json.loads(proc.stdout or "[]")
            running_machine = next((m for m in machines if m.get("Running")), None)
            if not running_machine:
                result["error"] = "Nenhuma podman machine em estado Running"
                return result

            name = running_machine.get("Name", "")
            result["machine_name"] = name

            proc2 = subprocess.run(
                ["podman", "machine", "inspect", name],
                capture_output=True, text=True, timeout=15,
            )
            if proc2.returncode != 0:
                result["error"] = proc2.stderr.strip() or f"podman machine inspect {name} failed"
                return result

            info_list = json.loads(proc2.stdout or "[]")
            info = info_list[0] if info_list else {}

            if current_platform == "Darwin":
                socket_path = (
                    info.get("ConnectionInfo", {})
                    .get("PodmanSocket", {})
                    .get("Path", "")
                )
                if not socket_path:
                    socket_path = info.get("ConnectionInfo", {}).get("URI", "")
                docker_host_uri = f"unix://{socket_path}" if socket_path else ""
            else:  # Windows
                socket_path = r"\\.\pipe\podman-machine-default"
                docker_host_uri = "npipe:////./pipe/podman-machine-default"

            result.update({
                "socket_path": socket_path,
                "docker_host_uri": docker_host_uri,
                "service_running": bool(socket_path),
                "ryuk_disabled": False,  # VM-based: Ryuk geralmente funciona
            })

        except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError, KeyError) as exc:
            result["error"] = str(exc)

    return result


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Docker/Podman build runner utilities for ava-stack-build-validator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--normalize-path",
        metavar="PATH",
        help="Normalize a host path for use in container -v flags.",
    )
    group.add_argument(
        "--image",
        nargs=2,
        metavar=("FRAMEWORK", "VERSION"),
        help=(
            "Resolve container image for framework+version. E.g.: dotnet 10.0, node 20. "
            "For Node-based frontend frameworks pass the Node.js version here or use "
            "--node-version to override (see --node-version)."
        ),
    )
    group.add_argument(
        "--volumes",
        nargs=2,
        metavar=("TARGET", "PROJECT_NAME"),
        help="Print -v flags for cache volumes. E.g.: backend Meu-ERP",
    )
    group.add_argument(
        "--read-node-version",
        metavar="DOCKERFILE_PATH",
        help="Extract Node.js major version from a Dockerfile.",
    )
    group.add_argument(
        "--platform",
        dest="detect_platform",
        action="store_true",
        help="Detect and print --platform flag for containers (ARM hosts).",
    )
    group.add_argument(
        "--detect-runtime",
        metavar="PREFERRED",
        help="Detect available container runtime. PREFERRED: docker|podman|auto.",
    )
    group.add_argument(
        "--runtime-info",
        metavar="RUNTIME",
        help=(
            "Check runtime health. Returns JSON: "
            "{runtime, version, available, service_running, method, error}."
        ),
    )
    group.add_argument(
        "--podman-socket",
        dest="podman_socket",
        action="store_true",
        help=(
            "Detect Podman socket and return configuration info as JSON. "
            "Exit code: 0 if service_running=true, 1 otherwise. "
            "Output: {available, socket_path, docker_host_uri, rootless, "
            "service_running, ryuk_disabled, platform, machine_name, "
            "error, docker_host_already_set}."
        ),
    )

    # Optional modifiers (not mutually exclusive with the main action group)
    parser.add_argument(
        "--runtime",
        metavar="RUNTIME",
        default="docker",
        help=(
            "Container runtime in use (docker or podman). Used by --normalize-path "
            "to emit the correct path format on Windows + Git Bash / MSYS2 hosts. "
            "Default: docker."
        ),
    )
    parser.add_argument(
        "--node-version",
        metavar="NODE_VERSION",
        default="",
        help=(
            "Node.js major version to use for Node-based frontend images. "
            "Overrides the VERSION argument of --image when the framework is "
            "angular, react, vue, or svelte. Use this when you hold the framework "
            "version (e.g. Angular 17) separately from the Node.js version (e.g. 20). "
            "Example: --image angular 17 --node-version 20  →  node:20-alpine."
        ),
    )

    args = parser.parse_args()

    if args.normalize_path is not None:
        print(normalize_path_for_docker(args.normalize_path, runtime=args.runtime))

    elif args.image is not None:
        framework, version = args.image
        print(resolve_image(framework, version, node_version=args.node_version))

    elif args.volumes is not None:
        target, project_name = args.volumes
        for flag in get_volume_flags(target, project_name):
            print(flag)

    elif args.read_node_version is not None:
        print(read_node_version_from_dockerfile(args.read_node_version))

    elif args.detect_platform:
        # May output empty string — that's intentional (no flag needed on x86)
        print(detect_platform_flag())

    elif args.detect_runtime is not None:
        print(detect_runtime(args.detect_runtime))

    elif args.runtime_info is not None:
        print(json.dumps(get_runtime_info(args.runtime_info), indent=2))

    elif args.podman_socket:
        info = get_podman_socket_info()
        print(json.dumps(info, indent=2))
        sys.exit(0 if info["service_running"] else 1)


if __name__ == "__main__":
    main()
