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


def _all_units_report(status: jubilant.Status, app: str, message: str) -> bool:
    """Report whether every unit of *app* is active with the given workload status message.

    This is used as a ``juju.wait`` ready condition so that the wait does not return until the
    config-changed event has actually been processed on every unit and the status message
    updated — not merely until the units are idle.
    """
    app_info = status.apps.get(app)
    if app_info is None:
        return False
    if app_info.app_status.current != "active":
        return False
    if not app_info.units:
        return False
    for unit in app_info.units.values():
        if unit.workload_status.current != "active":
            return False
        if unit.workload_status.message != message:
            return False
    return True


@pytest.mark.juju_setup
def test_deploy(charm: pathlib.Path, juju: jubilant.Juju):
    """Deploy the charm under test with two units."""
    resources = {
        "demo-server-image": METADATA["resources"]["demo-server-image"]["upstream-source"]
    }
    juju.deploy(charm, app=APP_NAME, resources=resources, num_units=2)
    juju.wait(jubilant.all_active)


def test_all_units_get_config_changed(juju: jubilant.Juju):
    """Verify that a config change fires config-changed on every unit, not just the leader.

    The charm sets its unit status to ``log-level=<value>`` in the config-changed handler.
    After changing the ``log-level`` config, every unit's workload status message should
    reflect the new value. If only the leader received config-changed, the non-leader unit
    would still show the old value.
    """
    expected = "log-level=debug"
    juju.config(APP_NAME, {"log-level": "debug"})
    juju.wait(lambda status: _all_units_report(status, APP_NAME, expected))

    status = juju.status()
    units = status.apps[APP_NAME].units
    assert len(units) == 2, f"expected 2 units, got {len(units)}"

    for unit_name, unit in units.items():
        message = unit.workload_status.message
        assert message == expected, (
            f"unit {unit_name} did not get config-changed: status message is {message!r}"
        )
