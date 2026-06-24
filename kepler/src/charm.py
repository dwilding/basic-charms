#!/usr/bin/env python3

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

"""Kubernetes charm for a demo app."""

import logging

import ops
from charmlibs import pathops

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


class KosmosCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, framework: ops.Framework) -> None:
        super().__init__(framework)
        self.pebble_service_name = "fastapi-service"
        framework.observe(self.on["demo-server"].pebble_ready, self._on_demo_server_pebble_ready)
        framework.observe(self.on.update_backup_action, self._on_update_backup)

    def _on_update_backup(self, event: ops.ActionEvent) -> None:
        """Overwrite the backup file in the workload container.

        The backup file is expected to be host-mounted at
        ``/etc/myapp/backup.yaml`` (see the unit test). We remove the existing
        file before writing the new contents, to emulate a charm that clears a
        stale file before writing fresh data.
        """
        container = self.unit.get_container("demo-server")
        if not container.can_connect():
            event.fail("workload container is not ready")
            return
        data = event.params["data"]
        backup_root = pathops.ContainerPath("/etc/myapp", container=container)
        backup_file = backup_root / "backup.yaml"
        # Remove any existing file before writing, so that we write a fresh file
        # rather than appending to / modifying stale contents.
        backup_file.unlink(missing_ok=True)
        backup_file.write_text(data)
        event.set_results({"written": data})

    def _on_demo_server_pebble_ready(self, event: ops.PebbleReadyEvent) -> None:
        """Define and start a workload using the Pebble API."""
        # Get a reference the container attribute on the PebbleReadyEvent
        container = event.workload
        # Add initial Pebble config layer using the Pebble API
        container.add_layer("fastapi_demo", self._get_pebble_layer(), combine=True)
        # Make Pebble reevaluate its plan, ensuring any services are started if enabled.
        container.replan()
        # Learn more about statuses at
        # https://documentation.ubuntu.com/juju/3.6/reference/status/
        self.unit.status = ops.ActiveStatus()

    def _get_pebble_layer(self) -> ops.pebble.Layer:
        """Pebble layer for the FastAPI demo services."""
        command = " ".join(
            [
                "uvicorn",
                "api_demo_server.app:app",
                "--host=0.0.0.0",
                "--port=8000",
            ]
        )
        pebble_layer: ops.pebble.LayerDict = {
            "summary": "FastAPI demo service",
            "description": "pebble config layer for FastAPI demo server",
            "services": {
                self.pebble_service_name: {
                    "override": "replace",
                    "summary": "fastapi demo",
                    "command": command,
                    "startup": "enabled",
                }
            },
        }
        return ops.pebble.Layer(pebble_layer)


if __name__ == "__main__":  # pragma: nocover
    ops.main(KosmosCharm)
