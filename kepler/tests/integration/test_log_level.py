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

"""Differential test: does log_level = INFO filter DEBUG logs from caplog?

The same test runs in two charms.  One charm (kepler) has log_level = "INFO"
set in pyproject.toml alongside log_file_level = "DEBUG"; the other (kosmos)
has only log_file_level = "DEBUG".  The test emits a DEBUG log via the
jubilant.wait logger and asserts it appears in caplog records.

Without log_level, pytest's log_file_level = DEBUG lowers the root logger to
DEBUG and the caplog handler (left at NOTSET) captures DEBUG records.  With
log_level = INFO, the caplog handler is raised to INFO and filters them out.
"""

import logging

import pytest

_WAIT_LOGGER = logging.getLogger("jubilant.wait")
_DEBUG_MESSAGE = "differential test: debug log from jubilant.wait"


@pytest.mark.xfail(strict=True, reason="log_level=INFO filters DEBUG from caplog")
def test_debug_log_from_jubilant_wait_is_captured(caplog: pytest.LogCaptureFixture):
    """Assert that a DEBUG log from jubilant.wait appears in caplog records."""
    _WAIT_LOGGER.debug(_DEBUG_MESSAGE)
    captured = [record.getMessage() for record in caplog.records]
    assert _DEBUG_MESSAGE in captured
