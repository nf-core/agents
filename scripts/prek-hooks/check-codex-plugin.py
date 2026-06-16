#!/usr/bin/env python3
"""Validate Codex plugin manifests and repo marketplace wiring."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
INSTALLATION = {"AVAILABLE", "INSTALLED_BY_DEFAULT", "NOT_AVAILABLE"}
AUTHENTICATION = {"ON_INSTALL", "ON_FIRST_USE"}
PATH_FIELDS = ("skills", "mcpServers", "apps")


def fail(msg: str) -> None:
    print(f"check-codex-plugin: {msg}", file=sys.stderr)
    sys.exit(1)


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001
        fail(f"{path}: invalid JSON: {exc}")


def require_obj(value: object, path: Path | str) -> dict:
    if not isinstance(value, dict):
        fail(f"{path}: expected JSON object")
    return value


def iter_paths(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return []


def check_rel_path(path_value: str, base: Path, label: str, require_exists: bool = True) -> None:
    if not path_value.startswith("./"):
        fail(f"{label}: path must start with './': {path_value}")
    resolved = (base / path_value).resolve()
    try:
        resolved.relative_to(base.resolve())
    except ValueError:
        fail(f"{label}: path must stay inside plugin root: {path_value}")
    if require_exists and not resolved.exists():
        fail(f"{label}: path does not exist: {path_value}")


def check_manifest(path: Path) -> str:
    manifest = require_obj(load_json(path), path)
    plugin_root = path.parent.parent

    name = manifest.get("name")
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        fail(f"{path}: name must be stable lowercase kebab/dot-case")

    for field in ("version", "description"):
        if field in manifest and not isinstance(manifest[field], str):
            fail(f"{path}: {field} must be a string")

    author = manifest.get("author")
    if author is not None:
        author = require_obj(author, f"{path}: author")
        if not isinstance(author.get("name"), str) or not author["name"]:
            fail(f"{path}: author.name must be a non-empty string")

    for field in PATH_FIELDS:
        if field not in manifest:
            continue
        values = iter_paths(manifest[field])
        if not values:
            fail(f"{path}: {field} must be a './'-prefixed path or list of paths")
        for value in values:
            check_rel_path(value, plugin_root, f"{path}: {field}")

    if "hooks" in manifest:
        hooks = manifest["hooks"]
        if isinstance(hooks, (dict, list)):
            pass
        else:
            values = iter_paths(hooks)
            if not values:
                fail(f"{path}: hooks must be path, list of paths, inline object, or list")
            for value in values:
                check_rel_path(value, plugin_root, f"{path}: hooks")

    interface = manifest.get("interface")
    if interface is not None:
        interface = require_obj(interface, f"{path}: interface")
        prompts = interface.get("defaultPrompt")
        if prompts is not None and not (
            isinstance(prompts, list) and all(isinstance(item, str) for item in prompts)
        ):
            fail(f"{path}: interface.defaultPrompt must be a list of strings")
        for asset_field in ("composerIcon", "logo"):
            if isinstance(interface.get(asset_field), str) and interface[asset_field].startswith("./"):
                check_rel_path(interface[asset_field], plugin_root, f"{path}: interface.{asset_field}")
        screenshots = interface.get("screenshots")
        if screenshots is not None:
            if not isinstance(screenshots, list) or not all(isinstance(item, str) for item in screenshots):
                fail(f"{path}: interface.screenshots must be a list of strings")
            for screenshot in screenshots:
                if screenshot.startswith("./"):
                    check_rel_path(screenshot, plugin_root, f"{path}: interface.screenshots")

    return name


def check_marketplace(path: Path) -> None:
    marketplace = require_obj(load_json(path), path)
    market_root = path.parent.parent.parent
    if not isinstance(marketplace.get("name"), str) or not marketplace["name"]:
        fail(f"{path}: name must be a non-empty string")
    interface = require_obj(marketplace.get("interface", {}), f"{path}: interface")
    if not isinstance(interface.get("displayName"), str) or not interface["displayName"]:
        fail(f"{path}: interface.displayName is required for Codex marketplace display")
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        fail(f"{path}: plugins must be a non-empty array")

    for idx, plugin in enumerate(plugins):
        if not isinstance(plugin, dict):
            fail(f"{path}: plugins[{idx}] must be an object")
        name = plugin.get("name")
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            fail(f"{path}: plugins[{idx}].name must be stable lowercase kebab/dot-case")
        source = plugin.get("source")
        if isinstance(source, str):
            source_path = source
        elif isinstance(source, dict) and source.get("source") == "local" and isinstance(source.get("path"), str):
            source_path = source["path"]
        else:
            fail(f"{path}: plugins[{idx}].source must be a local './' path or local source object")
        check_rel_path(source_path, market_root, f"{path}: plugins[{idx}].source.path")
        manifest_path = (market_root / source_path / ".codex-plugin" / "plugin.json").resolve()
        if not manifest_path.exists():
            fail(f"{path}: plugins[{idx}] missing .codex-plugin/plugin.json at {source_path}")
        manifest_name = check_manifest(manifest_path)
        if manifest_name != name:
            fail(f"{path}: plugins[{idx}].name {name!r} does not match manifest name {manifest_name!r}")
        policy = require_obj(plugin.get("policy", {}), f"{path}: plugins[{idx}].policy")
        if policy.get("installation") not in INSTALLATION:
            fail(f"{path}: plugins[{idx}].policy.installation must be one of {sorted(INSTALLATION)}")
        if policy.get("authentication") not in AUTHENTICATION:
            fail(f"{path}: plugins[{idx}].policy.authentication must be one of {sorted(AUTHENTICATION)}")
        if not isinstance(plugin.get("category"), str) or not plugin["category"]:
            fail(f"{path}: plugins[{idx}].category is required")


def main(argv: list[str]) -> int:
    paths = [Path(arg) for arg in argv[1:]]
    if not paths:
        paths = list(ROOT.glob("plugins/*/.codex-plugin/plugin.json")) + list(ROOT.glob(".agents/plugins/marketplace.json"))
    for path in paths:
        if path.name != "plugin.json" and path.name != "marketplace.json":
            continue
        if path.name == "plugin.json":
            check_manifest(path)
        else:
            check_marketplace(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
