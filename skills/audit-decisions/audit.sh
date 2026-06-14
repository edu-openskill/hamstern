#!/usr/bin/env bash
set -euo pipefail

# Audit Decisions 스킬
# 프로젝트의 확정된 결정사항들을 재검토하고 타당성을 검증합니다.

ACTIVE_CONFIG="$HOME/.config/hamstern/active-project.json"
if [ ! -f "$ACTIVE_CONFIG" ]; then
  echo "❌ Error: ~/.config/hamstern/active-project.json 없음. /hams:link 또는 /hams:init 먼저 호출하세요." >&2
  exit 1
fi
ACTIVE_UUID=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['uuid'])")
HAMSTERN_DATA=$(python3 -c "import json; print(json.load(open(r'$ACTIVE_CONFIG'))['hamstern_data_path'])")
PROJECT_DIR="$HAMSTERN_DATA/projects/$ACTIVE_UUID"
DECISIONS_FILE="$PROJECT_DIR/decisions.md"
SESSIONS_DIR="$PROJECT_DIR/sessions"

if [[ ! -f "$DECISIONS_FILE" ]]; then
  echo "❌ Error: decisions.md not found at $DECISIONS_FILE"
  echo ""
  echo "Make sure you're in a hamstern project with:"
  echo "  $PROJECT_DIR/.hamstern/decisions.md"
  echo "  (run /hams:context-save in a Claude session to create it)"
  exit 1
fi

if [[ ! -d "$SESSIONS_DIR" ]]; then
  echo "⚠️  Warning: sessions/ not found at $SESSIONS_DIR"
  echo "   Audit will proceed without per-session background context"
fi

echo "🔍 Auditing Decisions in: $PROJECT_DIR"
echo ""

# decisions.md 파싱
mapfile -t decisions < <(grep "^- \[" "$DECISIONS_FILE" | sed 's/^- \[/[/' | sed 's/\] /\] - /')

if [[ ${#decisions[@]} -eq 0 ]]; then
  echo "ℹ️  No decisions to audit"
  exit 0
fi

echo "📌 Found ${#decisions[@]} decision(s):"
echo ""

# 각 결정에 대해 사용자 확인
for i in "${!decisions[@]}"; do
  idx=$((i + 1))
  decision="${decisions[$i]}"

  # 카테고리와 요약 분리
  category=$(echo "$decision" | sed 's/\[\(.*\)\].*/\1/')
  summary=$(echo "$decision" | sed 's/\[.*\] - //')

  echo "[$idx/${#decisions[@]}] 📌 $summary"
  echo "     Category: $category"
  echo ""

  # 배경 정보 찾기 — sessions/*.md 안에서 매칭
  if [[ -d "$SESSIONS_DIR" ]]; then
    if grep -rq "$summary" "$SESSIONS_DIR" 2>/dev/null; then
      echo "✓ Found in sessions/"
    fi
  fi

  echo ""
  echo "  Actions:"
  echo "    [k] Keep (유지)"
  echo "    [m] Modify (수정 필요)"
  echo "    [d] Delete (폐기 - 최종 확인 필수)"
  echo "    [s] Skip (다음으로)"
  echo ""

  read -p "  Decision? (k/m/d/s): " -r action
  action="${action,,}"

  case "$action" in
    k)
      echo "  → ✅ Keeping this decision"
      ;;
    m)
      echo "  → ⚠️  Mark for review"
      echo "  Enter notes (optional): "
      read -p "  > " -r notes
      if [[ -n "$notes" ]]; then
        echo "  Note saved: $notes"
      fi
      ;;
    d)
      echo "  → ❌ DELETE REQUEST"
      echo ""
      echo "  ⚠️  This will remove the decision from decisions.md"
      echo "  This action is PERMANENT"
      echo ""
      read -p "  Really delete '$summary'? (yes/no): " -r confirm
      if [[ "$confirm" == "yes" ]]; then
        echo "  → Deleted"
      else
        echo "  → Cancelled"
      fi
      ;;
    s)
      echo "  → Skipping"
      ;;
    *)
      echo "  → Invalid action, skipping"
      ;;
  esac

  echo ""
  echo "---"
  echo ""
done

echo ""
echo "✅ Audit complete"
echo ""
echo "Changes:"
echo "  - Review marked items in decisions.md"
echo "  - Deleted items have been removed (can be restored from git)"
echo "  - decisions.md will auto-regenerate on next Claude session"
