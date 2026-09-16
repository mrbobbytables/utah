"""Unit tests for scripts/check-parity.py derivation and parsing logic."""

from __future__ import annotations

import importlib.util
import tomllib
import pytest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

spec = importlib.util.spec_from_file_location(
    "check_parity", REPO_ROOT / "scripts" / "check-parity.py"
)
check_parity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_parity)

expand_braces = check_parity.expand_braces
derive_effective_payload = check_parity.derive_effective_payload
format_toml = check_parity.format_toml


def test_expand_braces_single():
    assert expand_braces("package") == ["package"]


def test_expand_braces_variants():
    assert sorted(expand_braces("gstreamer1-{plugins-base,plugins-good}")) == [
        "gstreamer1-plugins-base",
        "gstreamer1-plugins-good",
    ]
    assert sorted(expand_braces("pkg{,-devel}")) == ["pkg", "pkg-devel"]


def test_derive_effective_payload_basic():
    base_toml = """
[fedora]
packages = [
    "pkg01", "pkg02", "pkg03", "pkg04", "pkg05",
    "pkg06", "pkg07", "pkg08", "pkg09", "pkg10",
    "pkg11", "pkg12", "pkg13", "pkg14", "pkg15",
    "pkg16", "pkg17", "pkg18", "pkg19", "pkg20"
]

[multimedia_overrides]
packages = ["ffmpeg"]

[excluded]
packages = ["nano"]
"""

    packages_sh = """
#!/usr/bin/env bash
# Some comments
copr_install_isolated "ublue-os/packages" "uupd"

dnf5 -y install \\
    --enablerepo="tailscale-stable" \\
    tailscale

dnf5 -y install \\
    --enablerepo="fedora-multimedia" \\
    --exclude=excluded-codec \\
    gstreamer1-plugins-{bad,ugly}
"""

    payload = derive_effective_payload(base_toml, packages_sh)
    assert len(payload["fedora"]) == 20
    assert "uupd" in payload["external"]
    assert "tailscale" in payload["external"]
    assert "gstreamer1-plugins-bad" in payload["multimedia"]
    assert "gstreamer1-plugins-ugly" in payload["multimedia"]
    assert "excluded-codec" not in payload["multimedia"]
    assert payload["multimedia_overrides"] == ["ffmpeg"]
    assert payload["excluded"] == ["nano"]


def test_derive_effective_payload_floor_assertions():
    # Fewer than 20 Fedora packages should fail loudly
    low_fedora = """
[fedora]
packages = ["single-pkg"]
"""
    packages_sh = """
copr_install_isolated "ublue-os/packages" "uupd"
dnf install tailscale
"""
    with pytest.raises(ValueError, match="parsed 1 base Fedora packages, expected at least 20"):
        derive_effective_payload(low_fedora, packages_sh)

    # Fewer than 2 external packages should fail loudly
    valid_fedora = """
[fedora]
packages = [
    "p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08", "p09", "p10",
    "p11", "p12", "p13", "p14", "p15", "p16", "p17", "p18", "p19", "p20"
]
"""
    empty_packages_sh = "# No packages"
    with pytest.raises(ValueError, match="parsed 0 external packages, expected at least 2"):
        derive_effective_payload(valid_fedora, empty_packages_sh)


def test_format_toml_roundtrip():
    payload = {
        "fedora": ["curl", "git"],
        "external": ["tailscale", "uupd"],
        "multimedia": ["ffmpeg"],
        "multimedia_overrides": ["pipewire"],
        "excluded": ["nano"],
    }
    toml_str = format_toml(payload)
    data = tomllib.loads(toml_str)
    assert data["fedora"]["packages"] == ["curl", "git"]
    assert data["external"]["packages"] == ["tailscale", "uupd"]
    assert data["multimedia"]["packages"] == ["ffmpeg"]
    assert data["multimedia_overrides"]["packages"] == ["pipewire"]
    assert data["excluded"]["packages"] == ["nano"]
