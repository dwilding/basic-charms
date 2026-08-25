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


@pytest.mark.xfail(
    strict=True,
    reason="without log_level=INFO, Jubilant INFO logs are not captured",
)
def test_jubilant_info_logs_captured(
    charm: pathlib.Path, juju: jubilant.Juju, caplog: pytest.LogCaptureFixture
):
    """Jubilant's INFO logs must be retained in pytest's captured-log section."""
    juju.wait(jubilant.all_active)
    # Force Jubilant's logger to emit at INFO (the level the doc claim concerns) so the
    # assertion is deterministic regardless of how Jubilant configures its own logger.
    jubilant_logger = logging.getLogger("jubilant")
    jubilant_logger.setLevel(logging.INFO)
    jubilant_logger.info("integration test info probe")
    captured_info = [
        record
        for record in caplog.records
        if (record.name == "jubilant" or record.name.startswith("jubilant."))
        and record.levelno >= logging.INFO
    ]
    assert captured_info, "expected Jubilant INFO logs to be retained in caplog"
