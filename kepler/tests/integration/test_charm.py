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
# The integration tests use the Jubilant library and the pytest-jubilant plugin.
# See https://documentation.ubuntu.com/ops/latest/howto/write-integration-tests-for-a-charm/
#
# pytest-jubilant provides a module-scoped `juju` fixture that creates a temporary Juju model.
# The `charm` fixture is defined in conftest.py.

import logging
import pathlib
import re

import jubilant
import pytest
import yaml

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(pathlib.Path("charmcraft.yaml").read_text())
APP_NAME = METADATA["name"]


@pytest.mark.juju_setup
def test_deploy(charm: pathlib.Path, juju: jubilant.Juju):
    """Deploy the charm under test."""
    resources = {
        "demo-server-image": METADATA["resources"]["demo-server-image"]["upstream-source"]
    }
    juju.deploy(charm, app=APP_NAME, resources=resources)
    juju.wait(jubilant.all_active)


def _locked_ops_version() -> str:
    """Return the ops version pinned in this charm's uv.lock."""
    text = pathlib.Path("uv.lock").read_text()
    match = re.search(r'^name = "ops"\nversion = "([^"]+)"', text, re.MULTILINE)
    assert match is not None, "ops package not found in uv.lock"
    return match.group(1)


def test_ops_runtime_version_matches_lock(juju: jubilant.Juju):
    """The ops version in the deployed unit venv must equal the version locked in uv.lock.

    The Ops security doc claims a charm's uv.lock influences the runtime versions of its
    dependencies: charmcraft pack installs from the lock into the unit's venv, so the locked
    version is the version that runs. We deploy the charm, read ops.__version__ from the unit
    venv (the doc's own verification command), and assert it equals the locked version.
    """
    lock_version = _locked_ops_version()
    task = juju.exec(
        "bash",
        "-c",
        "/var/lib/juju/agents/unit-*/charm/venv/bin/python "
        '-c "import ops; print(ops.__version__)"',
        unit=f"{APP_NAME}/0",
    )
    runtime_version = task.stdout.strip()
    assert runtime_version == lock_version, (
        f"runtime ops {runtime_version!r} does not match locked ops {lock_version!r}"
    )
