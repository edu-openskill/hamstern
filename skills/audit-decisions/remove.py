"""Direct args form for /hams:audit-decisions:

    /hams:audit-decisions remove "<text>"

decisions.md 의 `- <text>` 또는 `- <text> <!-- session: ... -->` 첫 매칭 줄 삭제 +
decisions-log.md 에 제거 이벤트 append.

Stdlib only. 디렉터리명에 하이픈이 있어 import 측은 importlib.util 로 로드.
"""
import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SESSION_MARKER_RE = re.compile(r"\s*<!--\s*session:\s*\S+?\s*-->\s*$")


@dataclass
class RemoveResult:
    removed: bool
    line: str = ""
    reason: str = ""


def _strip_marker(body: str) -> str:
    return SESSION_MARKER_RE.sub("", body).rstrip()


def run(project_root: Path, text: str) -> RemoveResult:
    project_root = Path(project_root)
    decisions_file = project_root / ".hamstern" / "decisions.md"
    log_file = project_root / ".hamstern" / "decisions-log.md"

    if not decisions_file.is_file():
        return RemoveResult(removed=False, reason=f"decisions.md not found at {decisions_file}")

    target = text.strip()
    lines = decisions_file.read_text(encoding="utf-8").splitlines()
    out_lines = []
    removed_line = None
    for ln in lines:
        if removed_line is None and ln.startswith("- "):
            body = _strip_marker(ln[2:])
            if body == target:
                removed_line = ln
                continue  # skip this line
        out_lines.append(ln)

    if removed_line is None:
        return RemoveResult(removed=False, reason=f"no matching decision for: {target!r}")

    decisions_file.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    entry = (
        f"\n---\n\n## {ts} | 핀 제거\n"
        f"- **결정:** {target}\n"
        f"- **제거 이유:** dashboard 에서 × 클릭 (사용자 세션 명령)\n"
    )
    if not log_file.exists():
        log_file.write_text("# Decisions Log\n<!-- append-only. 수동 편집 금지. -->\n", encoding="utf-8")
    with log_file.open("a", encoding="utf-8") as f:
        f.write(entry)

    return RemoveResult(removed=True, line=removed_line)


def main():
    parser = argparse.ArgumentParser(description="Remove a decision by exact body match")
    parser.add_argument("text", help="결정 본문 (앞의 '- ' 와 trailing session 마커 제외)")
    parser.add_argument("--project", default=".", help="프로젝트 루트")
    args = parser.parse_args()
    result = run(project_root=Path(args.project).resolve(), text=args.text)
    if not result.removed:
        print(f"error: {result.reason}", file=sys.stderr)
        sys.exit(1)
    print(f"removed: {result.line}")


if __name__ == "__main__":
    main()
