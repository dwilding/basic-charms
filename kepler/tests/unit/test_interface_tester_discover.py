# Copyright 2026 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Adversarial test for the documentation claim in canonical/operator PR #2710:
# that running `interface_tester discover --include <name>` from a `charmlibs`
# repository root verifies an interface's schema and tests.
#
# `pytest-interface-tester` 3.4.1 cannot be installed next to this charm: its
# transitive dependency `ops-scenario>=7.0.1` pins `ops~=2.15`, which conflicts
# with this charm's `ops~=3.7`. The discovery contract below is a faithful,
# minimal copy of `interface_tester.collector.collect_tests` and the
# `_gather_*` helpers it calls (tag 3.4.1): only the parts that decide *whether*
# any versions and test cases are discovered are kept; the schema/charm loading
# that only runs after a version directory is found is omitted. The two
# `pathlib.Path.glob` calls and the `tests_dir` default are reproduced verbatim.

import importlib
import inspect
import logging
import sys
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("interface_tests_checker")

_DEFAULT_TESTS_DIR = "interface_tests"


class Role(str, Enum):
    provider = "provider"
    requirer = "requirer"


def _scrape_module_for_tests(module: Any) -> list[Any]:
    tests: list[Any] = []
    for _, obj in inspect.getmembers(module):
        if inspect.isfunction(obj):
            tests.append(obj)
    return tests


def _gather_test_cases_for_version(
    version_dir: Path, *, tests_dir: str = _DEFAULT_TESTS_DIR
) -> tuple[list[Any], list[Any]]:
    interface_tests_dir = version_dir / tests_dir
    provider_test_cases: list[Any] = []
    requirer_test_cases: list[Any] = []
    if interface_tests_dir.exists():
        sys.path.append(str(interface_tests_dir))
        for role in Role:
            module_name = "test_requirer" if role is Role.requirer else "test_provider"
            sys.modules.pop(module_name, None)
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                logger.warning("Failed to load module %s", module_name)
                continue
            tests = _scrape_module_for_tests(module)
            sys.modules.pop(module_name, None)
            target = provider_test_cases if role is Role.provider else requirer_test_cases
            target.extend(tests)
        sys.path.pop(-1)
    return provider_test_cases, requirer_test_cases


def _gather_tests_for_interface(
    interface_dir: Path, *, tests_dir: str = _DEFAULT_TESTS_DIR
) -> dict[str, dict[str, list[Any]]]:
    tests: dict[str, dict[str, list[Any]]] = {}
    for version_dir in interface_dir.glob("v*"):
        provider_test_cases, requirer_test_cases = _gather_test_cases_for_version(
            version_dir, tests_dir=tests_dir
        )
        tests[version_dir.name] = {
            "provider": provider_test_cases,
            "requirer": requirer_test_cases,
        }
    return tests


def collect_tests(
    path: Path, include: str = "*", *, tests_dir: str = _DEFAULT_TESTS_DIR
) -> dict[str, dict[str, dict[str, list[Any]]]]:
    """Discovery contract copied from interface_tester.collector.collect_tests (3.4.1)."""
    tests: dict[str, dict[str, dict[str, list[Any]]]] = {}
    for interface_dir in (path / "interfaces").glob(include):
        interface_dir_name = interface_dir.name
        if interface_dir_name.startswith("__"):
            continue
        interface_name = interface_dir_name.replace("-", "_")
        tests[interface_name] = _gather_tests_for_interface(interface_dir, tests_dir=tests_dir)
    return tests


def _make_charmlibs_layout(root: Path, name: str = "my_fancy_database") -> Path:
    version = root / "interfaces" / name / "interface" / "v1"
    (version / "tests").mkdir(parents=True)
    (version / "tests" / "test_provider.py").write_text(
        "def test_provider_passes() -> None:\n    pass\n"
    )
    (version / "tests" / "test_requirer.py").write_text(
        "def test_requirer_passes() -> None:\n    pass\n"
    )
    return root


def _make_legacy_layout(root: Path, name: str = "my_fancy_database") -> Path:
    version = root / "interfaces" / name / "v1"
    (version / "interface_tests").mkdir(parents=True)
    (version / "interface_tests" / "test_provider.py").write_text(
        "def test_provider_passes() -> None:\n    pass\n"
    )
    return root


def test_charmlibs_layout_yields_no_discovered_tests(tmp_path: Path) -> None:
    """Charmlibs layout is not discovered: collect_tests finds no version directories."""
    root = _make_charmlibs_layout(tmp_path)
    saved_path = list(sys.path)
    try:
        result = collect_tests(root, include="my_fancy_database")
    finally:
        sys.path[:] = saved_path
    # The interface directory exists and matches the --include glob, so the
    # interface key is present; but `interface_dir.glob("v*")` finds nothing
    # because charmlibs nests versions under `interface/` rather than directly
    # under `interfaces/<name>/`. So no versions (and thus no tests or schema)
    # are discovered, even though real tests live at
    # interfaces/<name>/interface/v1/tests/. `interface_tester discover` would
    # therefore print `my_fancy_database: <no tests>`.
    assert "my_fancy_database" in result
    assert result["my_fancy_database"] == {}


def test_legacy_layout_is_discovered(tmp_path: Path) -> None:
    """Legacy charm-relation-interfaces layout IS discovered: control for the logic."""
    root = _make_legacy_layout(tmp_path)
    saved_path = list(sys.path)
    try:
        result = collect_tests(root, include="my_fancy_database")
    finally:
        sys.path[:] = saved_path
    assert "my_fancy_database" in result
    assert "v1" in result["my_fancy_database"]
    assert result["my_fancy_database"]["v1"]["provider"], "expected provider tests discovered"
