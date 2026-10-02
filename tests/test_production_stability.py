from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_defaults_target_coolify_domain():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'SITE_URL = os.getenv("SITE_URL", "https://teranga-ai.fr").rstrip("/")' in app
    assert "teranga-ai-1.onrender.com" not in app


def test_public_errors_do_not_reference_render():
    errors = (ROOT / "services" / "errors.py").read_text(encoding="utf-8")
    assert "Render" not in errors


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
