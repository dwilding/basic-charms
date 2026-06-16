#!/usr/bin/env python3
# Copyright 2026 Charmer
# See LICENSE file for licensing details.

"""Charm the application."""

import logging

import ops

# A standalone module for workload-specific logic (no charming concerns):
import meteor

logger = logging.getLogger(__name__)


class MeteorCharm(ops.CharmBase):
    """Charm the application."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        framework.observe(self.on.install, self._on_install)
        framework.observe(self.on.start, self._on_start)
        framework.observe(
            self.on.relation_write_relation_created,
            self._on_relation_write_changed,
        )
        framework.observe(
            self.on.relation_write_relation_joined,
            self._on_relation_write_changed,
        )
        framework.observe(
            self.on.relation_write_relation_changed,
            self._on_relation_write_changed,
        )

    def _on_install(self, event: ops.InstallEvent):
        """Install the workload on the machine."""
        meteor.install()

    def _on_start(self, event: ops.StartEvent):
        """Handle start event."""
        self.unit.status = ops.MaintenanceStatus("starting workload")
        meteor.start()
        version = meteor.get_version()
        if version is not None:
            self.unit.set_workload_version(version)
        self.unit.status = ops.ActiveStatus()

    def _on_relation_write_changed(self, event: ops.RelationEvent):
        """Exercise app databag permissions and expose outcomes via unit status.

        Claim under test: only the leader can write the local application databag.
        """
        if self.unit.is_leader():
            event.relation.data[self.app]["leader-write"] = "ok"
            self.unit.status = ops.ActiveStatus("app-write:leader-success")
            return

        try:
            event.relation.data[self.app]["nonleader-write"] = "blocked"
            self.unit.status = ops.ActiveStatus("app-write:nonleader-unexpected-success")
        except ops.ModelError:
            self.unit.status = ops.ActiveStatus("app-write:nonleader-modelerror")


if __name__ == "__main__":  # pragma: nocover
    ops.main(MeteorCharm)
