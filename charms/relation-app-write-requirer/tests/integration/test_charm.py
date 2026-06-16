# Copyright 2026 Charmer
# See LICENSE file for licensing details.

"""Integration tests for relation-app-write-requirer charm."""

import logging
import pathlib

import jubilant
import pytest

logger = logging.getLogger(__name__)


@pytest.mark.juju_setup
def test_deploy_requirer(requirer_charm: pathlib.Path, juju: jubilant.Juju):
    """Deploy the requirer charm."""
    juju.deploy(requirer_charm, app="requirer")
    juju.wait(jubilant.all_active)
    status = juju.status()
    assert "requirer" in status.apps
