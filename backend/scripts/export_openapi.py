import argparse
import json
from pathlib import Path

from app.main import app

OUTPUT = Path(__file__).resolve().parents[1] / "openapi.json"


def render_schema() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the FastAPI OpenAPI schema")
    parser.add_argument("--check", action="store_true", help="fail when openapi.json is stale")
    args = parser.parse_args()

    rendered = render_schema()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != rendered:
            print("openapi.json is stale; run `uv run python scripts/export_openapi.py`")
            return 1
        return 0

    OUTPUT.write_text(rendered)
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
