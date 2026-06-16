# Copyright 2026 Charmer
# See LICENSE file for licensing details.
#
# The integration tests use the Jubilant library and the pytest-jubilant plugin.
# See https://documentation.ubuntu.com/ops/latest/howto/write-integration-tests-for-a-charm/
#
# pytest-jubilant provides a module-scoped `juju` fixture that creates a temporary Juju model.
# The `charm` fixture is defined in conftest.py.

import pathlib

import jubilant
import pytest


@pytest.mark.juju_setup
def test_relation_app_databag_write_requires_leadership(
    charm: pathlib.Path,
    micron_charm: pathlib.Path,
    juju: jubilant.Juju,
):
    """Validate claim 4 with real relation events in a multi-unit deployment.

    Claim: writing to the app databag is leader-only, and non-leader attempts
    fail with a ModelError.
    """
    juju.deploy(charm, app="meteor", num_units=2)
    juju.deploy(micron_charm, app="micron", num_units=1)
    juju.wait(lambda status: jubilant.all_active(status, "meteor", "micron"))

    juju.integrate("meteor:relation-write", "micron:relation-write")

    def relation_signals_ready(status: jubilant.Status) -> bool:
        if "meteor" not in status.apps:
            return False
        if len(status.apps["meteor"].units) < 2:
            return False
        return all(
            unit.is_active and unit.workload_status.message.startswith("app-write:")
            for unit in status.apps["meteor"].units.values()
        )

    juju.wait(
        relation_signals_ready,
        error=lambda status: jubilant.any_error(status, "meteor", "micron"),
    )

    status = juju.status()
    meteor_units = status.apps["meteor"].units
    assert len(meteor_units) >= 2

    leaders = [unit for unit in meteor_units.values() if unit.leader]
    nonleaders = [unit for unit in meteor_units.values() if not unit.leader]
    assert len(leaders) == 1
    assert len(nonleaders) >= 1

    assert leaders[0].workload_status.message == "app-write:leader-success"

    for unit in nonleaders:
        assert unit.workload_status.message == "app-write:nonleader-modelerror"
