# Copyright 2026 Charmer
# See LICENSE file for licensing details.
#
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

import pytest
from ops import testing

from charm import MeteorCharm


def mock_get_version():
    """Get a mock version string without executing the workload code."""
    return "1.0.0"


def test_start(monkeypatch: pytest.MonkeyPatch):
    """Test that the charm has the correct state after handling the start event."""
    # Arrange:
    ctx = testing.Context(MeteorCharm)
    monkeypatch.setattr("charm.meteor.get_version", mock_get_version)
    # Act:
    state_out = ctx.run(ctx.on.start(), testing.State())
    # Assert:
    assert state_out.workload_version is not None
    assert state_out.unit_status == testing.ActiveStatus()


def test_do_backup_action_raises_action_failed():
    """Verify the doc claim that calling event.fail() raises ActionFailed.

    The ops "How to manage actions" docs state that, in unit tests, if the
    charm code calls ``event.fail()`` to indicate that the action has failed,
    an ``ActionFailed`` exception will be raised. This test attempts to refute
    that claim by running an action whose handler calls ``event.fail()`` and
    checking that no exception is raised. If the claim is true, the
    ``pytest.raises`` block succeeds and the test passes.
    """
    ctx = testing.Context(MeteorCharm)

    with pytest.raises(testing.ActionFailed) as exc_info:
        ctx.run(ctx.on.action('do-backup'), testing.State())

    assert exc_info.value.message == "sorry, couldn't do the backup"
    # The output state is still available on the exception.
    assert exc_info.value.state is not None
