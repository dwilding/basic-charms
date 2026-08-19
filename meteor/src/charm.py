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
        framework.observe(self.on["do-backup"].action, self._on_do_backup_action)

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

    def _on_do_backup_action(self, event: ops.ActionEvent):
        """Handle the do-backup action.

        The backup is not implemented, so the action always fails.
        """
        event.fail("sorry, couldn't do the backup")


if __name__ == "__main__":  # pragma: nocover
    ops.main(MeteorCharm)
