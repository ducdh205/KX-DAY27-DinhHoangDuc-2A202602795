"""Record a real Exercise 1 run; optionally read public GitHub PRs without a PAT.

Run from the repository root with ``uv run python -m reports.exercise_1.run_live``.
The optional anonymous mode changes only request headers in this process.
It still fetches live GitHub data and calls the configured LLM.
"""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
import time

from dotenv import load_dotenv
from rich.console import Console

from common import github
from common.schemas import AUTO_APPROVE_THRESHOLD, ESCALATE_THRESHOLD
from exercises import exercise_1_confidence as exercise


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--anonymous-public-read", action="store_true")
    args = parser.parse_args()
    console = Console(record=True, width=100)
    exercise.console = console
    read_mode = "authenticated"
    if args.anonymous_public_read and not os.environ.get("GITHUB_TOKEN"):
        read_mode = "anonymous_public_api"

        def public_headers(accept="application/vnd.github+json"):
            return {
                "Accept": accept,
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "Day27-HITL-Lab",
            }

        github._headers = public_headers

    started = time.monotonic()
    record = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "pr_url": args.pr,
        "github_read_mode": read_mode,
        "model": os.environ.get("LLM_MODEL", "openai/gpt-4o-mini"),
        "python": sys.version.split()[0],
        "packages": {name: version(name) for name in ("langgraph", "langchain-openai", "pydantic")},
        "thresholds": {"auto_approve": AUTO_APPROVE_THRESHOLD, "escalate": ESCALATE_THRESHOLD},
        "source_sha256": {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (Path(exercise.__file__).relative_to(Path.cwd()), Path("common/schemas.py"))
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    console.rule("Exercise 1 — live evidence")
    console.print(f"PR: {args.pr}\nGitHub read mode: {read_mode}")
    try:
        final = exercise.build_graph().invoke({"pr_url": args.pr})
        record["status"] = "completed"
        record["result"] = {
            **final,
            "analysis": final["analysis"].model_dump(mode="json"),
        }
        console.rule("Final")
        console.print(f"confidence = {final['analysis'].confidence:.0%}")
        console.print(f"action     = {final.get('final_action')}")
        console.print(f"reasoning  = {final['analysis'].confidence_reasoning}")
    except Exception as exc:
        record["status"] = "failed"
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        console.print(f"FAILED: {type(exc).__name__}: {exc}")
        raise
    finally:
        record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        record["duration_seconds"] = round(time.monotonic() - started, 3)
        args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        console.save_text(str(args.output.with_suffix(".txt")))


if __name__ == "__main__":
    main()
