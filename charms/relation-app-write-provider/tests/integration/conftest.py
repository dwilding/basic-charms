# Copyright 2026 Charmer
# See LICENSE file for licensing details.
#
# The integration tests use the Jubilant library and the pytest-jubilant plugin.
# See https://documentation.ubuntu.com/ops/latest/howto/write-integration-tests-for-a-charm/

import os
import pathlib

import pytest


@pytest.fixture(scope="session")
def provider_charm():
    """Return the path of the provider charm under test."""
    charm = os.environ.get("CHARM_PATH")
    if not charm:
        charm_dir = pathlib.Path()
        charms = list(charm_dir.glob("*.charm"))
        assert charms, f"No charms were found in {charm_dir.absolute()}"
        assert len(charms) == 1, f"Found more than one charm {charms}"
        charm = charms[0]
    path = pathlib.Path(charm).resolve()
    assert path.is_file(), f"{path} is not a file"
    return path


@pytest.fixture(scope="session")
def requirer_charm():
    """Return the path of the requirer charm."""
    # In a real scenario, this would be built separately or come from another source.
    # For now, we assume it's available via REQUIRER_CHARM_PATH or in the same dir.
    charm_path = os.environ.get("REQUIRER_CHARM_PATH")
    if charm_path:
        path = pathlib.Path(charm_path).resolve()
        assert path.is_file(), f"{path} is not a file"
        return path
    # Fallback: not available, tests will skip
    return None
