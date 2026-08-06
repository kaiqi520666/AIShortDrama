import argparse
import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_DIR = BACKEND_DIR.parent
CONTRACT_PATH = REPOSITORY_DIR / "contracts" / "generation-capabilities.v1.json"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.model_capabilities import capabilities_payload  # noqa: E402


def render_contract() -> str:
    return json.dumps(capabilities_payload(), ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="导出生成模型能力契约")
    parser.add_argument("--check", action="store_true", help="仅校验契约是否为最新")
    args = parser.parse_args()
    content = render_contract()
    if args.check:
        if not CONTRACT_PATH.exists() or CONTRACT_PATH.read_text(encoding="utf-8") != content:
            print("生成能力契约已过期，请运行 export_generation_capabilities.py")
            return 1
        return 0
    CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT_PATH.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
