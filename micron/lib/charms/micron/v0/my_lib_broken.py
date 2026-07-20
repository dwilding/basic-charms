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

from typing import Any

import ops


class DatabaseReadyEvent(ops.EventBase):
    """Event representing that the database is ready."""

    def __init__(self, handle: ops.Handle, *, credential_secret: ops.Secret):
        super().__init__(handle)
        self.credential_secret = credential_secret

    def snapshot(self) -> dict[str, str]:
        data = super().snapshot()
        # Store the label (rather than the id, as in the docs) so that the
        # event restores correctly under ops-scenario, where a unit-owned
        # secret's ``id`` is ``None``.
        data['credential_secret_label'] = self.credential_secret.label
        return data

    def restore(self, snapshot: dict[str, Any]):
        super().restore(snapshot)
        credential_secret_label = snapshot['credential_secret_label']
        self.credential_secret = self.framework.model.get_secret(
            label=credential_secret_label
        )


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
        # Emit `ready` with the unit's secret so the custom event is observable.
        secret = self.framework.model.get_secret(label='db-creds')
        self.on.ready.emit(credential_secret=secret)
