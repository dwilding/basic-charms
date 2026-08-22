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

"""Tests validating the ops 'manage actions' unit-test example.

The docs (https://canonical.com/juju/docs/ops/latest/howto/manage-actions/#write-unit-tests)
show a snapshot action handler that calls ``event.set_results({'result': msg})``
and then a unit test that asserts ``'snapshot-size' in ctx.action_results``.

The handler only ever sets a ``result`` key, so ``snapshot-size`` cannot be
present in the results. This test asserts that understanding: if it passes, the
documented assertion would fail and the doc example is incorrect.
"""

from ops import testing

from charm import KosmosCharm


def test_snapshot_action_does_not_set_snapshot_size():
    """The snapshot action sets 'result', not 'snapshot-size'."""
    ctx = testing.Context(KosmosCharm)
    ctx.run(
        ctx.on.action("snapshot", params={"filename": "db-snapshot.tar.gz"}),
        testing.State(),
    )
    # The doc's handler sets results to {'result': msg}, so 'snapshot-size'
    # is absent. The documented assertion ``'snapshot-size' in
    # ctx.action_results`` would therefore fail.
    assert "snapshot-size" not in ctx.action_results
    assert ctx.action_results == {"result": "Stored snapshot in db-snapshot.tar.gz."}
