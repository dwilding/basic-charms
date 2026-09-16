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
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

import ops
from ops import testing

from charm import KosmosCharm


def test_pebble_layer():
    ctx = testing.Context(KosmosCharm)
    container = testing.Container(name="demo-server", can_connect=True)
    state_in = testing.State(
        containers={container},
        leader=True,
    )
    state_out = ctx.run(ctx.on.pebble_ready(container), state_in)
    # Expected plan after Pebble ready with default config
    expected_plan = {
        "services": {
            "fastapi-service": {
                "override": "replace",
                "summary": "fastapi demo",
                "command": "uvicorn api_demo_server.app:app --host=0.0.0.0 --port=8000",
                "startup": "enabled",
                # Since the environment is empty, Layer.to_dict() will not
                # include it.
            }
        }
    }

    # Check that we have the plan we expected:
    assert state_out.get_container(container.name).plan == expected_plan
    # Check the unit is active and reports the default log-level:
    assert state_out.unit_status == testing.ActiveStatus("log-level=info")
    # Check the service was started:
    assert (
        state_out.get_container(container.name).service_statuses["fastapi-service"]
        == ops.pebble.ServiceStatus.ACTIVE
    )


def test_config_changed_updates_status():
    """A config-changed event updates the unit status to reflect the new log-level."""
    ctx = testing.Context(KosmosCharm)
    container = testing.Container(name="demo-server", can_connect=True)
    state_in = testing.State(
        containers={container},
        leader=True,
        config={"log-level": "debug"},
    )
    state_out = ctx.run(ctx.on.config_changed(), state_in)
    assert state_out.unit_status == testing.ActiveStatus("log-level=debug")


def test_config_changed_survives_pebble_ready():
    """The status set by config-changed survives a subsequent pebble-ready event.

    This mirrors the real event sequence on a unit: config-changed and pebble-ready
    both fire during the initial deploy, and both handlers set the status from the
    same config value, so the observable is preserved across the full sequence.
    """
    ctx = testing.Context(KosmosCharm)
    container = testing.Container(name="demo-server", can_connect=True)
    state = testing.State(
        containers={container},
        leader=True,
        config={"log-level": "debug"},
    )
    state = ctx.run(ctx.on.config_changed(), state)
    state = ctx.run(ctx.on.pebble_ready(container), state)
    assert state.unit_status == testing.ActiveStatus("log-level=debug")
