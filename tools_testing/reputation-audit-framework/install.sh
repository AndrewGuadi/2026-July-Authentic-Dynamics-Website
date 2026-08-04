#!/usr/bin/env bash
# One-command installer for reputation-audit-framework (Linux/macOS).
#   curl -sSL ./install.sh | bash     — or —     ./install.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${ROOT}/.venv"
PY="${PYTHON_BIN:-python3}"

printf '\n\033[1;32m[+]\033[0m reputation-audit-framework installer\n'

if ! command -v "${PY}" >/dev/null 2>&1; then
  printf '\033[1;31m[!]\033[0m python3 not found on PATH\n' >&2
  exit 1
fi

VER="$("${PY}" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
REQUIRED="3.11"
if [ "$(printf '%s\n%s\n' "${REQUIRED}" "${VER}" | sort -V | head -n1)" != "${REQUIRED}" ]; then
  printf '\033[1;31m[!]\033[0m Python %s+ required, found %s\n' "${REQUIRED}" "${VER}" >&2
  exit 1
fi

printf '\033[1;32m[+]\033[0m creating virtualenv at %s\n' "${VENV}"
"${PY}" -m venv "${VENV}"
# shellcheck disable=SC1091
source "${VENV}/bin/activate"

python -m pip install --upgrade pip wheel >/dev/null
python -m pip install -r "${ROOT}/requirements.txt"

mkdir -p "${ROOT}/output" "${ROOT}/images"

printf '\033[1;32m[+]\033[0m checking optional collectors\n'
for bin in docker exiftool amass maigret social-analyzer recon-cli alephclient trufflehog wkhtmltopdf; do
  if command -v "${bin}" >/dev/null 2>&1; then
    printf '    \033[0;32mok\033[0m       %s\n' "${bin}"
  else
    printf '    \033[0;33mmissing\033[0m  %s (docker fallback will be used where configured)\n' "${bin}"
  fi
done

cat <<'EOF'

[+] install complete

    source .venv/bin/activate
    python main.py doctor
    make docker-build-all
    make entity-up
    make doctor-all
    python main.py run --full-name "Sarah Mitchell" \
      --domain "sarahmitchellhomes.com" \
      --username "sarahmitchellrealtor" \
      --image-dir "./images" --authorized yes

    Docker path:  docker compose run --rm audit run --help

EOF
