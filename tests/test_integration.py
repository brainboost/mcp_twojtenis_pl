from twojtenis_mcp.config import Config


def test_config_has_new_api_url():
    cfg = Config()
    assert cfg.main_api_url == "https://app-twojtenis-api-p-weu.azurewebsites.net"
    assert cfg.request_timeout == 30
    assert cfg.auth0_domain == "twojtenis.eu.auth0.com"
    assert cfg.auth0_audience == "https://api.twojetenis.pl"


def test_main_api_url_env_override(monkeypatch):
    monkeypatch.setenv("TWOJTENIS_MAIN_API_URL", "https://override.example")
    cfg = Config()
    assert cfg.main_api_url == "https://override.example"


def test_request_timeout_env_override(monkeypatch):
    monkeypatch.setenv("TWOJTENIS_REQUEST_TIMEOUT", "10")
    cfg = Config()
    assert cfg.request_timeout == 10
