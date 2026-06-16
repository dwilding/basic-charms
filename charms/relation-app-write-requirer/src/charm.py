#!/usr/bin/env python3
# Copyright 2026 Charmer
# See LICENSE file for licensing details.

"""Requirer charm for testing relation app databag write permissions."""

import logging

import ops

logger = logging.getLogger(__name__)


class RelationAppWriteRequirerCharm(ops.CharmBase):
    """Charm that tests leadership constraints on relation app databag writes."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        framework.observe(
            self.on.test_app_write_relation_created,
            self._on_relation_created,
        )
        framework.observe(
            self.on.test_app_write_relation_joined,
            self._on_relation_joined,
        )

    def _on_relation_created(self, event: ops.RelationCreatedEvent) -> None:
        """Handle relation-created event and attempt app databag write."""
        is_leader = self.unit.is_leader()
        logger.info(
            f"Requirer relation_created on {self.unit.name}, is_leader={is_leader}"
        )

        try:
            # Attempt to write to app databag
            event.relation.data[self.app]["requirer_app_status"] = "created"
            logger.info(
                f"Requirer {self.unit.name}: Successfully wrote to app databag"
            )
        except ops.ModelError as e:
            logger.error(
                f"Requirer {self.unit.name}: Failed to write app databag: {e}"
            )

    def _on_relation_joined(self, event: ops.RelationJoinedEvent) -> None:
        """Handle relation-joined event and attempt app databag write."""
        is_leader = self.unit.is_leader()
        logger.info(
            f"Requirer relation_joined on {self.unit.name}, is_leader={is_leader}"
        )

        try:
            # Attempt to write to app databag
            event.relation.data[self.app]["requirer_units_joined"] = str(
                len(event.relation.units)
            )
            logger.info(
                f"Requirer {self.unit.name}: Successfully wrote to app databag"
            )
        except ops.ModelError as e:
            logger.error(
                f"Requirer {self.unit.name}: Failed to write app databag: {e}"
            )


if __name__ == "__main__":  # pragma: nocover
    ops.main(RelationAppWriteRequirerCharm)
