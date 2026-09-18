#!/usr/bin/bash

# shellcheck source=/dev/null
source /usr/lib/ublue/setup-services/libsetup.sh

# If Tailscale is not installed, defer configuration without failing.
# This keeps first boot clean and makes the deferred state explicit.
if ! command -v tailscale >/dev/null 2>&1; then
    echo "Tailscale binary not found; skipping Tailscale configuration (deferred)."
    exit 0
fi

version-script tailscale privileged 1 || exit 0

set -xeuo pipefail

OPERATOR_UID="${PKEXEC_UID:-${UID:-$(id -u)}}"
OPERATOR="$(getent passwd "${OPERATOR_UID}" | cut -d: -f1)"

if [ -n "${OPERATOR}" ]; then
    tailscale set --operator="${OPERATOR}" || {
        echo "Warning: tailscale set --operator failed (tailscaled daemon may not be active yet)."
    }
fi
