"""Page du planificateur + son script statique, textes réinjectés.

Le script vit dans static/trip-planner.js et lit ses textes traduits dans le
bloc JSON #trip-config. Pour les tests de contrat, on reconstitue ce que le
navigateur exécute : la page, puis le script avec les valeurs de la config.
"""

import json
import re
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "static" / "trip-planner.js"


def with_planner_script(html):
    match = re.search(r'<script type="application/json" id="trip-config">(.*?)</script>', html, re.S)
    if not match:
        return html
    config = json.loads(match.group(1))
    js = SCRIPT.read_text(encoding="utf-8")
    js = re.sub(r"(['\"])\+CFG\.(\w+)\+\1", lambda m: str(config[m.group(2)]), js)
    js = re.sub(r"\bCFG\.(\w+)", lambda m: json.dumps(config[m.group(1)], ensure_ascii=False), js)
    return html + "\n<script>\n" + js + "\n</script>"
