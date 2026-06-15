from twojtenis_mcp.config import Config


def test_config_has_catalog_api_url(monkeypatch):
    monkeypatch.setenv("TWOJTENIS_CATALOG_API_URL", "https://app-twojtenis-api-p-weu.azurewebsites.net")
    cfg = Config()
    assert cfg.catalog_api_url == "https://app-twojtenis-api-p-weu.azurewebsites.net"
    assert cfg.request_timeout == 30
    assert cfg.auth0_domain == "twojtenis.eu.auth0.com"
    assert cfg.auth0_audience == "https://api.twojetenis.pl"


def test_deprecated_main_api_url_env_accepted(monkeypatch):
    monkeypatch.delenv("TWOJTENIS_CATALOG_API_URL", raising=False)
    monkeypatch.setenv("TWOJTENIS_MAIN_API_URL", "https://override.example")
    cfg = Config()
    assert cfg.catalog_api_url == "https://override.example"


def test_request_timeout_env_override(monkeypatch):
    monkeypatch.setenv("TWOJTENIS_REQUEST_TIMEOUT", "10")
    cfg = Config()
    assert cfg.request_timeout == 10
