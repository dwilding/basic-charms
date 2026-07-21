# Copyright 2026 Charmer
# See LICENSE file for licensing details.

"""A demo relation wrapper library that does NOT support custom endpoint names.

This is the ``DatabaseRequirer`` shown verbatim in the "Write a library" section
of the Ops docs (with the constructor parameter renamed from ``relation_name``
to ``endpoint`` to match the docs' "Test custom endpoint names" test call
signature). It observes ``charm.on['database']`` regardless of the endpoint name
passed in -- that is, it does not honour the custom endpoint name.

See: https://canonical.com/juju/docs/ops/latest/howto/manage-libraries
"""

import ops


class DatabaseReadyEvent(ops.EventBase):
    """Event representing that the database is ready."""


class DatabaseRequirerEvents(ops.ObjectEvents):
    """Container for Database Requirer events."""

    ready = ops.EventSource(DatabaseReadyEvent)


class DatabaseRequirer(ops.Object):
    """Wrap the database relation endpoint, ignoring the endpoint name."""

    on = DatabaseRequirerEvents()

    def __init__(self, charm: ops.CharmBase, endpoint: str):
        super().__init__(charm, endpoint)
        self.framework.observe(
            charm.on['database'].relation_changed, self._on_db_changed
        )

    def _on_db_changed(self, event: ops.RelationChangedEvent):
        self.on.ready.emit()
