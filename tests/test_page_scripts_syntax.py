"""Every inline script served by the main pages must be valid JavaScript.

The trip planner script is generated from a Python f-string; a lost escape
(\\" → ") broke the whole page silently. Node checks the syntax.
"""

import os
import re
import shutil
import subprocess
import tempfile

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

NODE = shutil.which("node")
PAGES = [
    "/",
    "/trip-planner?lang=fr",
    "/trip-planner?lang=en",
    "/explorer",
    "/lieux",
    "/lieux/goree",
    "/dakar",
    "/regions/dakar",
    "/opportunities",
    "/partners",
]
SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)(?![^>]*application/ld\+json)[^>]*>(.*?)</script>", re.S)


@pytest.mark.skipif(NODE is None, reason="node non disponible")
@pytest.mark.parametrize("path", PAGES)
def test_inline_scripts_are_valid_javascript(path):
    from app import app

    response = app.test_client().get(path)
    assert response.status_code == 200
    scripts = SCRIPT.findall(response.get_data(as_text=True))
    for index, source in enumerate(scripts):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as handle:
            handle.write(source)
            name = handle.name
        try:
            result = subprocess.run([NODE, "--check", name], capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(name)
        assert result.returncode == 0, f"{path} script #{index}: {result.stderr[:500]}"
