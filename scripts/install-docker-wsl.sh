#!/usr/bin/env bash
set -euo pipefail

if ! grep -qi microsoft /proc/version 2>/dev/null; then
  echo "This script is intended to run inside Ubuntu on WSL."
  exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
  exec sudo -E bash "$0" "$@"
fi

default_user="${SUDO_USER:-}"
if [ -z "$default_user" ] || [ "$default_user" = "root" ]; then
  default_user="$(awk -F: '$3 >= 1000 && $3 < 60000 && $1 != "nobody" { print $1; exit }' /etc/passwd)"
fi

. /etc/os-release
codename="${VERSION_CODENAME:-${UBUNTU_CODENAME:-}}"
if [ -z "$codename" ]; then
  echo "Unable to detect Ubuntu codename from /etc/os-release."
  exit 1
fi

echo "Installing independent Docker Engine for cae-cli on Ubuntu ${codename}..."

apt-get update
apt-get install -y ca-certificates curl gnupg

for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
  apt-get remove -y "$pkg" >/dev/null 2>&1 || true
done

install -m 0755 -d /etc/apt/keyrings
if [ ! -s /etc/apt/keyrings/docker.asc ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
fi
chmod a+r /etc/apt/keyrings/docker.asc

arch="$(dpkg --print-architecture)"
rm -f /etc/apt/sources.list.d/docker.list
cat >/etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${codename}
Components: stable
Architectures: ${arch}
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

groupadd -f docker
if [ -n "$default_user" ]; then
  usermod -aG docker "$default_user"
  echo "Added ${default_user} to the docker group."
fi

if command -v systemctl >/dev/null 2>&1 && [ -d /run/systemd/system ]; then
  systemctl enable --now docker
else
  service docker start
fi

docker version

if [ -n "${CAE_DOCKER_REGISTRY_MIRRORS:-}" ]; then
  echo "Configuring Docker registry mirrors from CAE_DOCKER_REGISTRY_MIRRORS..."
  mkdir -p /etc/docker
  mirrors_json="$(printf '%s' "$CAE_DOCKER_REGISTRY_MIRRORS" | awk -v q='"' '
    BEGIN { FS=","; printf "[" }
    {
      for (i = 1; i <= NF; i++) {
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", $i)
        if ($i != "") {
          if (n++) printf ","
          printf "%s%s%s", q, $i, q
        }
      }
    }
    END { printf "]" }
  ')"
  cat >/etc/docker/daemon.json <<EOF
{
  "registry-mirrors": ${mirrors_json}
}
EOF
  if command -v systemctl >/dev/null 2>&1 && [ -d /run/systemd/system ]; then
    systemctl restart docker
  else
    service docker restart
  fi
fi

repo_root="${CAE_CLI_REPO_ROOT:-}"
if [ -z "$repo_root" ]; then
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  repo_root="$(cd "$script_dir/.." && pwd)"
fi
compose_file="${repo_root}/docker.yml"

core_images=(
  "unifem/calculix-desktop:latest"
)

extra_images=(
  "parallelworks/calculix:v2.15_exo"
  "simvia/code_aster:stable"
  "microfluidica/openfoam:11"
  "eperera/elmerfem:latest"
)

pull_set="${CAE_DOCKER_PULL_SET:-core}"
images_to_pull=("${core_images[@]}")
if [ "$pull_set" = "all" ]; then
  images_to_pull+=("${extra_images[@]}")
fi

echo "Pulling cae-cli Docker images (${pull_set})..."
for image in "${images_to_pull[@]}"; do
  echo "Pulling ${image}"
  docker pull "$image"
done

if [ -f "$compose_file" ]; then
  echo "Building cae-cli runtime through ${compose_file}..."
  docker rm -f cae-cli >/dev/null 2>&1 || true
  docker network rm cae-cli >/dev/null 2>&1 || true
  docker compose -f "$compose_file" up --build --remove-orphans cae-cli
else
  echo "docker.yml not found at ${compose_file}; falling back to direct image tag."
  docker network inspect cae-cli >/dev/null 2>&1 || docker network create cae-cli >/dev/null
  docker volume inspect cae-cli-work >/dev/null 2>&1 || docker volume create cae-cli-work >/dev/null
  docker tag unifem/calculix-desktop:latest cae-cli:latest
  docker rm -f cae-cli >/dev/null 2>&1 || true
  docker create \
    --name cae-cli \
    --network cae-cli \
    -v cae-cli-work:/work \
    -w /work \
    cae-cli:latest \
    /tmp/calculix/ccx_2.13_MT -v >/dev/null
fi
docker tag cae-cli:latest cae-cli:calculix

docker run --rm hello-world

echo
echo "Local cae-cli Docker resources:"
if [ -f "$compose_file" ]; then
  docker compose -f "$compose_file" ps -a
fi
docker image ls 'cae-cli*'
docker network ls --filter name='cae-cli'
docker volume ls --filter name='cae-cli'

echo
echo "Docker is installed and working inside WSL for cae-cli."
echo "The reusable Compose entry is: docker compose -f docker.yml up --build cae-cli"
echo "Use the local CalculiX image with: cae docker calculix model.inp --image cae-cli"
echo "If docker group changes do not apply immediately, close and reopen Ubuntu."
