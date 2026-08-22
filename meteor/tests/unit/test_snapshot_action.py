# Copyright 2026 Charmer
# See LICENSE file for licensing details.
#
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

"""Adversarial tests for the ops 'manage actions' howto unit-test example.

The howto's snapshot action handler ends with
``event.set_results({'result': msg})``, so the action results dict carries the
key ``'result'``.  The howto's unit test, however, asserts
``'snapshot-size' in ctx.action_results``.  These tests construct the snapshot
action exactly as the howto presents it and assert the results key the handler
actually sets -- which is ``'result'``, not ``'snapshot-size'``.
"""

from ops import testing

from charm import MeteorCharm


def test_snapshot_action_results_key_is_result_not_snapshot_size():
    """The howto's snapshot handler sets results with key 'result', not 'snapshot-size'."""
    ctx = testing.Context(MeteorCharm)
    ctx.run(
        ctx.on.action("snapshot", params={"filename": "db-snapshot.tar.gz"}),
        testing.State(),
    )
    # The handler logs that it is generating the snapshot.
    assert ctx.action_logs == ["Generating snapshot into db-snapshot.tar.gz"]
    # The handler ends with event.set_results({'result': msg}).
    results = ctx.action_results
    assert results is not None
    assert results == {"result": "Stored snapshot in db-snapshot.tar.gz."}
    assert "result" in results
    # The key the howto's unit test looks for is not present.
    assert "snapshot-size" not in results
