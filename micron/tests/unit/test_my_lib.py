# Copyright 2026 Charmer
# See LICENSE file for licensing details.

"""Adversarial test of the "Test custom endpoint names" docs section.

See: https://canonical.com/juju/docs/ops/latest/howto/manage-libraries

The docs' "Test custom endpoint names" section claims its test pattern
"verifies that the charm executes regardless of how we name the requirer
endpoint." That test only runs the ``start`` event and checks ``saw_start``, so
it never exercises the relation endpoint and cannot tell whether the wrapper
actually honours the custom endpoint name.

This file runs two parametrised tests against two libraries:

* ``my_lib.DatabaseRequirer`` -- observes ``charm.on[endpoint]``, so it honours
  the custom endpoint name.
* ``my_lib_broken.DatabaseRequirer`` -- observes ``charm.on['database']``
  regardless of the endpoint name passed in (this is the ``DatabaseRequirer``
  shown verbatim in the docs' "Write a library" section).

The two tests:

* ``test_docs_start_pattern`` reproduces the docs' verbatim test pattern (run
  ``start``, check ``saw_start``). It **passes for both** libraries -- proving
  the docs' test pattern cannot distinguish a wrapper that honours the custom
  endpoint name from one that ignores it.
* ``test_custom_endpoint_name_emits_ready`` is a genuine verification: fire
  ``relation_changed`` on the custom endpoint and assert ``ready`` fires. It
  passes for the correct library and **fails** for the broken one (marked
  ``xfail`` so CI stays green while still demonstrating the failure).
"""

import ops
import pytest
from ops import testing

from lib.charms.micron.v0.my_lib import DatabaseRequirer as CorrectDatabaseRequirer
from lib.charms.micron.v0.my_lib_broken import (
    DatabaseRequirer as BrokenDatabaseRequirer,
)


@pytest.mark.parametrize(
    "requirer_cls",
    [
        pytest.param(CorrectDatabaseRequirer, id="honours_endpoint_name"),
        pytest.param(BrokenDatabaseRequirer, id="ignores_endpoint_name"),
    ],
)
def test_docs_start_pattern(requirer_cls):
    """Reproduce the docs' verbatim "Test custom endpoint names" test pattern.

    This runs the ``start`` event and checks ``saw_start``, exactly as the docs
    show. It passes for *both* the correct and the broken library -- proving the
    docs' test pattern cannot distinguish a wrapper that honours the custom
    endpoint name from one that ignores it.
    """

    class MyTestCharm(ops.CharmBase):
        META = {
            "name": "my-charm",
            "requires": {
                "foo": {"interface": "my_interface"},
                "database": {"interface": "my_interface"},
            },
        }

        def __init__(self, framework: ops.Framework):
            super().__init__(framework)
            self.db = requirer_cls(self, endpoint="foo")
            framework.observe(self.on.start, self._on_start)
            self.saw_start = False

        def _on_start(self, _):
            self.saw_start = True

    ctx = testing.Context(MyTestCharm, meta=MyTestCharm.META)
    state_in = testing.State()

    with ctx(ctx.on.start(), state_in) as mgr:
        mgr.run()
        assert mgr.charm.saw_start


@pytest.mark.parametrize(
    "requirer_cls",
    [
        pytest.param(CorrectDatabaseRequirer, id="honours_endpoint_name"),
        pytest.param(
            BrokenDatabaseRequirer,
            id="ignores_endpoint_name",
            marks=pytest.mark.xfail(
                reason="the docs' 'Write a library' DatabaseRequirer hardcodes "
                "'database' and does not honour the custom endpoint name",
                strict=True,
            ),
        ),
    ],
)
def test_custom_endpoint_name_emits_ready(requirer_cls):
    """Fire relation_changed on the custom endpoint and assert ready is emitted."""

    # A charm that wraps a custom-named endpoint ('foo'), as the docs' "Test
    # custom endpoint names" section suggests a relation wrapper should support.
    # META includes 'database' too, so the broken library (which hardcodes
    # 'database') can still construct.
    class MyTestCharm(ops.CharmBase):
        META = {
            "name": "my-charm",
            "requires": {
                "foo": {"interface": "my_interface"},
                "database": {"interface": "my_interface"},
            },
        }

        def __init__(self, framework: ops.Framework):
            super().__init__(framework)
            self.db = requirer_cls(self, endpoint="foo")
            framework.observe(self.db.on.ready, self._on_db_ready)
            self.saw_ready = False

        def _on_db_ready(self, event):
            self.saw_ready = True

    ctx = testing.Context(MyTestCharm, meta=MyTestCharm.META)
    relation = testing.Relation("foo")
    state_in = testing.State(relations={relation})

    with ctx(ctx.on.relation_changed(relation), state_in) as mgr:
        mgr.run()
        assert mgr.charm.saw_ready
