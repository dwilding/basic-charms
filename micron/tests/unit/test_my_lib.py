# Copyright 2026 Charmer
# See LICENSE file for licensing details.

"""Adversarial test of the "Test custom endpoint names" docs section.

See: https://canonical.com/juju/docs/ops/latest/howto/manage-libraries

The docs' "Test custom endpoint names" section claims its test pattern
"verifies that the charm executes regardless of how we name the requirer
endpoint." That test only runs the ``start`` event and checks ``saw_start``, so
it never exercises the relation endpoint and cannot tell whether the wrapper
actually honours the custom endpoint name.

This file runs the *same* genuine verification against two libraries:

* ``my_lib.DatabaseRequirer`` -- correctly observes ``charm.on[endpoint]``, so
  it honours the custom endpoint name. The test passes.
* ``my_lib_broken.DatabaseRequirer`` -- observes ``charm.on['database']``
  regardless of the endpoint name passed in (this is the ``DatabaseRequirer``
  shown verbatim in the docs' "Write a library" section). The test fails, and
  is marked ``xfail`` so that CI stays green while still demonstrating the
  failure.

The verification: build a charm wrapping a custom-named endpoint, fire
``relation_changed`` on that endpoint, and assert the wrapper's ``ready``
custom event fires.
"""

import typing

import ops
import pytest
from ops import testing

from lib.charms.micron.v0.my_lib import DatabaseReadyEvent
from lib.charms.micron.v0.my_lib import DatabaseRequirer as CorrectDatabaseRequirer
from lib.charms.micron.v0.my_lib_broken import (
    DatabaseRequirer as BrokenDatabaseRequirer,
)


def _build_charm(requirer_cls):
    class MyTestCharm(ops.CharmBase):
        META = {
            "name": "my-charm",
            "requires": {
                "foo": {"interface": "my_interface"},
                # The broken library observes 'database' regardless of the
                # endpoint name passed in, so META must include it for that
                # library to construct:
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

    return MyTestCharm


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
    charm_type = _build_charm(requirer_cls)
    ctx = testing.Context(charm_type, meta=charm_type.META)
    relation = testing.Relation("foo")
    secret = testing.Secret(
        {"username": "admin", "password": "admin"},
        label="db-creds",
        owner="unit",
    )
    state_in = testing.State(relations={relation}, secrets={secret})

    with ctx(ctx.on.relation_changed(relation), state_in) as mgr:
        mgr.run()

    custom_event = ctx.emitted_events[-1]
    assert isinstance(custom_event, requirer_cls.on.ready.event_type)
    ready_event = typing.cast("DatabaseReadyEvent", custom_event)
    assert ready_event.credential_secret.label == secret.label
    assert mgr.charm.saw_ready
