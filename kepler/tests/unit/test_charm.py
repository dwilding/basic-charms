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
    # Check the unit is active:
    assert state_out.unit_status == testing.ActiveStatus()
    # Check the service was started:
    assert (
        state_out.get_container(container.name).service_statuses["fastapi-service"]
        == ops.pebble.ServiceStatus.ACTIVE
    )


def test_get_greeting_action_without_params():
    """The action handler reports the param is absent when no params are passed.

    The ops testing harness passes exactly the params you give it — it does not
    read ``default`` from the action metadata. This test validates the handler
    logic; the integration test checks whether Juju itself injects the default.
    """
    ctx = testing.Context(KosmosCharm)
    state_in = testing.State(leader=True)
    ctx.run(ctx.on.action("get-greeting"), state_in)
    assert ctx.action_results == {"name-present": "false", "name-value": ""}


def test_get_greeting_action_with_params():
    """The action handler reports the param value when it is explicitly passed."""
    ctx = testing.Context(KosmosCharm)
    state_in = testing.State(leader=True)
    ctx.run(ctx.on.action("get-greeting", params={"name": "alice"}), state_in)
    assert ctx.action_results == {"name-present": "true", "name-value": "alice"}
