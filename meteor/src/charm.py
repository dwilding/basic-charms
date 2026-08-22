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
        framework.observe(self.on["snapshot"].action, self._on_snapshot_action)

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

    def _on_snapshot_action(self, event: ops.ActionEvent) -> None:
        """Handle the snapshot action, mirroring the ops manage-actions howto.

        The howto's handler ends with ``event.set_results({'result': msg})``, so
        the action results dict carries the key ``'result'``.
        """
        # The howto uses event.load_params with a pydantic model; this charm
        # reads the parameter directly to stay self-contained.
        filename = str(event.params["filename"])
        # Let the user know we're working on it.
        event.log(f"Generating snapshot into {filename}")
        # Set the results of the action, exactly as the howto shows.
        msg = f"Stored snapshot in {filename}."
        event.set_results({"result": msg})


if __name__ == "__main__":  # pragma: nocover
    ops.main(MeteorCharm)
