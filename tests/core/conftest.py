"""Project-wide pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def reset_env_loaded_flag():
    """Reset core.secrets._env_loaded between tests.

    Plan-1 deferred-concerns item #1: the module-level flag conflates
    'we auto-tried' with 'don't try again', which silently breaks any
    test that places a fresh .env.local in tmp_path AFTER another test
    has already triggered the lazy auto-load.
    """
    import core.secrets

    core.secrets._env_loaded = False
    yield
    core.secrets._env_loaded = False
