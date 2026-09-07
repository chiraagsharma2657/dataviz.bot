"""When the landing page is shown, and which key gets used.

This was reported as "there is no landing page": a working .env silently
suppressed it, so it could not be previewed without breaking local setup.
REQUIRE_USER_KEY now decides, and these pin that.
"""

import pytest

from dataviz.landing import resolve_api_key


def test_server_key_is_used_when_nothing_forces_the_gate():
    assert resolve_api_key({"GOOGLE_API_KEY": "server-key"}) == "server-key"


def test_no_key_anywhere_shows_the_gate():
    assert resolve_api_key({}) is None


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " true "])
def test_require_user_key_beats_a_server_key(value):
    """The reported bug: a key in .env hid the landing page entirely."""
    env = {"GOOGLE_API_KEY": "server-key", "REQUIRE_USER_KEY": value}
    assert resolve_api_key(env) is None


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "maybe"])
def test_unset_or_falsy_flag_keeps_the_server_key(value):
    env = {"GOOGLE_API_KEY": "server-key", "REQUIRE_USER_KEY": value}
    assert resolve_api_key(env) == "server-key"


def test_empty_server_key_is_not_treated_as_a_key():
    assert resolve_api_key({"GOOGLE_API_KEY": ""}) is None


def test_reads_real_environment_by_default(monkeypatch):
    monkeypatch.delenv("REQUIRE_USER_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "from-env")
    assert resolve_api_key() == "from-env"

    monkeypatch.setenv("REQUIRE_USER_KEY", "true")
    assert resolve_api_key() is None
