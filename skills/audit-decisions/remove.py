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


def run(project_root: Path = None, text: str = "", base_dir: Path = None) -> RemoveResult:
    """
    Sub-F: base_dir 직접 지정 (hamstern-data/projects/{uuid}/) 우선.
    Sub-D/E: project_root 지정 → project_root/.hamstern/decisions.md.
    """
    if base_dir is None:
        if project_root is None:
            return RemoveResult(removed=False, reason="either project_root or base_dir required")
        base_dir = Path(project_root) / ".hamstern"

    base_dir = Path(base_dir)
    decisions_file = base_dir / "decisions.md"
    log_file = base_dir / "decisions-log.md"

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

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = (
        f"\n---\n\n## {ts} | 핀 제거\n"
        f"- **결정:** {target}\n"
        f"- **제거 이유:** dashboard 에서 × 클릭 (사용자 세션 명령)\n"
    )
    if not log_file.exists():
        log_file.write_text("# Decisions Log\n<!-- append-only. 수동 편집 금지. -->\n", encoding="utf-8")
    with log_file.open("a", encoding="utf-8") as f:
        f.write(entry)

    decisions_file.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    return RemoveResult(removed=True, line=removed_line)


def main():
    parser = argparse.ArgumentParser(description="Remove a decision by exact body match")
    parser.add_argument("text", help="결정 본문 (앞의 '- ' 와 trailing session 마커 제외)")
    parser.add_argument("--project", default=".", help="프로젝트 루트 (Sub-D/E 호환용)")
    parser.add_argument("--data-root", help="hamstern-data 의 project 디렉터리 (Sub-F)")
    parser.add_argument("--project-uuid", help="Sub-F: hamstern-data 의 project UUID (active-project.json 에서 hamstern_data_path 자동 resolve)")
    args = parser.parse_args()

    if args.project_uuid:
        import os, json
        active_config = os.path.expanduser("~/.config/hamstern/active-project.json")
        if not os.path.exists(active_config):
            print("error: ~/.config/hamstern/active-project.json 없음. /hams:link 또는 /hams:init 먼저.", file=sys.stderr)
            sys.exit(1)
        cfg = json.load(open(active_config, encoding="utf-8"))
        hamstern_data = cfg.get("hamstern_data_path")
        if not hamstern_data:
            print("error: active-project.json 에 hamstern_data_path 없음.", file=sys.stderr)
            sys.exit(1)
        base_dir = Path(hamstern_data) / "projects" / args.project_uuid
        if not base_dir.is_dir():
            print(f"error: project 디렉터리 없음: {base_dir}", file=sys.stderr)
            sys.exit(1)
        result = run(base_dir=base_dir, text=args.text)
    elif args.data_root:
        result = run(base_dir=Path(args.data_root).resolve(), text=args.text)
    else:
        result = run(project_root=Path(args.project).resolve(), text=args.text)

    if not result.removed:
        print(f"error: {result.reason}", file=sys.stderr)
        sys.exit(1)
    print(f"removed: {result.line}")


if __name__ == "__main__":
    main()
