from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_defaults_target_coolify_domain():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'SITE_URL = os.getenv("SITE_URL", "https://teranga-ai.fr").rstrip("/")' in app
    assert "teranga-ai-1.onrender.com" not in app


def test_public_errors_do_not_reference_render():
    errors = (ROOT / "services" / "errors.py").read_text(encoding="utf-8")
    assert "Render" not in errors


def test_public_errors_redact_query_tokens():
    from services.errors import public_error

    message = public_error(ValueError("https://example.test/?api_key=super-secret-token"))
    assert "super-secret-token" not in message


def test_docker_runtime_uses_coolify_port_and_exec():
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "exec gunicorn wsgi:app" in docker
    assert "GUNICORN_WORKERS:-2" in docker
    assert "GUNICORN_THREADS:-4" in docker
    assert "0.0.0.0:${PORT:-8000}" in docker


def test_dockerignore_excludes_local_and_test_files():
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "tests/" in dockerignore
    assert ".env" in dockerignore
    assert "__pycache__/" in dockerignore
    assert ".github" in dockerignore


def test_production_secret_contract_is_present():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert 'RUNTIME_ENV = os.getenv("TERANGA_ENV", "development")' in source
    assert 'len(_configured_secret) < 32' in source
    assert 'app.config["TRUSTED_HOSTS"]' in source


def test_security_headers_include_hsts_and_dns_prefetch_control():
    from app import app

    client = app.test_client()
    response = client.get("/health", base_url="https://teranga-ai.fr")
    assert response.headers["Strict-Transport-Security"].startswith("max-age=63072000")
    assert response.headers["X-DNS-Prefetch-Control"] == "off"


def test_public_auth_error_does_not_expose_secret_configuration():
    from services.errors import public_error

    message = public_error(RuntimeError("401 invalid api key"))
    assert "OPENAI_API_KEY" not in message
    assert "SECRET_KEY" not in message
