# Copyright 2026 Charmer
# See LICENSE file for licensing details.

"""A demo relation wrapper library that correctly supports custom endpoint names.

This is the ``DatabaseRequirer`` shown in the "Write a library" section of the
Ops docs, with the constructor parameter named ``endpoint`` (to match the call
signature used in the docs' "Test custom endpoint names" test) and the wrapper
observing ``charm.on[endpoint]`` -- that is, it honours the endpoint name
passed in, which is what supporting custom endpoint names actually requires.

See: https://canonical.com/juju/docs/ops/latest/howto/manage-libraries
"""

import ops


class DatabaseReadyEvent(ops.EventBase):
    """Event representing that the database is ready."""


class DatabaseRequirerEvents(ops.ObjectEvents):
    """Container for Database Requirer events."""

    ready = ops.EventSource(DatabaseReadyEvent)


class DatabaseRequirer(ops.Object):
    """Wrap the database relation endpoint, honouring the endpoint name."""

    on = DatabaseRequirerEvents()

    def __init__(self, charm: ops.CharmBase, endpoint: str):
        super().__init__(charm, endpoint)
        self.framework.observe(
            charm.on[endpoint].relation_changed, self._on_db_changed
        )

    def _on_db_changed(self, event: ops.RelationChangedEvent):
        self.on.ready.emit()
