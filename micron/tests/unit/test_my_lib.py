# Copyright 2026 Charmer
# See LICENSE file for licensing details.

"""Adversarial test of the "Test custom endpoint names" docs section.

See: https://canonical.com/juju/docs/ops/latest/howto/manage-libraries
"""

import ops
from ops import testing

from lib.charms.micron.v0.my_lib import DatabaseReadyEvent, DatabaseRequirer


class MyTestCharm(ops.CharmBase):
    META = {
        "name": "my-charm",
        "requires": {
            "foo": {"interface": "my_interface"},
            # The library (from the docs' "Write a library" section) hardcodes
            # 'database' as the endpoint it observes, so META must include it
            # for the library to construct:
            "database": {"interface": "my_interface"},
        },
    }

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        # Use a custom endpoint name, as the docs' "Test custom endpoint names"
        # section suggests a relation wrapper should support:
        self.db = DatabaseRequirer(self, endpoint="foo")
        framework.observe(self.db.on.ready, self._on_db_ready)
        self.saw_ready = False

    def _on_db_ready(self, event: DatabaseReadyEvent):
        self.saw_ready = True


def test_custom_endpoint_name_emits_ready():
    """Fire relation_changed on the custom endpoint and assert ready is emitted.

    This is what "verifying that custom endpoint names are supported" should
    mean: when the relation on the custom-named endpoint changes, the wrapper's
    custom event should fire.
    """
    ctx = testing.Context(MyTestCharm, meta=MyTestCharm.META)
    relation = testing.Relation("foo")
    secret = testing.Secret({"username": "admin", "password": "admin"}, label="db-creds")
    state_in = testing.State(relations={relation}, secrets={secret})

    with ctx(ctx.on.relation_changed(relation), state_in) as mgr:
        mgr.run()

    custom_event = ctx.emitted_events[-1]
    assert isinstance(custom_event, DatabaseReadyEvent)
    assert mgr.charm.saw_ready
