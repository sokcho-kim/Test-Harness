"""RegScan 프롬프트 추출기

RegScan prompts.py에서 현재 프롬프트를 evals/regscan/prompts/ 로 추출한다.
해시 비교로 동일 내용이면 스킵.

Usage:
    python scripts/export_regscan_prompts.py --version v4.0
    python scripts/export_regscan_prompts.py --version v4.1 --regscan-dir C:\\Jimin\\RegScan
"""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = HARNESS_DIR / "evals" / "regscan" / "prompts"
META_FILE = PROMPTS_DIR / "_meta.json"

DEFAULT_REGSCAN_DIR = Path(r"C:\Jimin\RegScan")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _get_regscan_commit(regscan_dir: Path) -> str:
    """RegScan 레포의 현재 git commit hash"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=regscan_dir,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _load_meta() -> dict:
    if META_FILE.exists():
        return json.loads(META_FILE.read_text(encoding="utf-8"))
    return {}


def _save_meta(meta: dict):
    META_FILE.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def export_prompts(version: str, regscan_dir: Path) -> bool:
    """RegScan prompts.py에서 V4 프롬프트를 추출.

    Returns True if new files were written, False if skipped (unchanged).
    """
    # RegScan을 import 경로에 추가
    regscan_root = str(regscan_dir)
    if regscan_root not in sys.path:
        sys.path.insert(0, regscan_root)

    try:
        from regscan.report.prompts import (
            BRIEFING_REPORT_PROMPT_V4,
            SYSTEM_PROMPT_V4,
        )
    except ImportError as e:
        print(f"ERROR: RegScan 프롬프트 import 실패: {e}")
        print(f"  경로 확인: {regscan_dir}")
        sys.exit(1)

    system_hash = _sha256(SYSTEM_PROMPT_V4)
    user_hash = _sha256(BRIEFING_REPORT_PROMPT_V4)
    combined_hash = _sha256(system_hash + user_hash)

    # 변경 감지
    meta = _load_meta()
    existing = meta.get(version, {})
    if existing.get("prompt_hash") == combined_hash:
        print(f"  SKIP: {version} - 프롬프트 변경 없음 (hash={combined_hash})")
        return False

    # 파일 저장
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    system_file = PROMPTS_DIR / f"{version}_system.txt"
    user_file = PROMPTS_DIR / f"{version}_user.txt"

    system_file.write_text(SYSTEM_PROMPT_V4, encoding="utf-8")
    user_file.write_text(BRIEFING_REPORT_PROMPT_V4, encoding="utf-8")

    # 메타데이터 업데이트
    regscan_commit = _get_regscan_commit(regscan_dir)
    meta[version] = {
        "version": version,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "regscan_commit": regscan_commit,
        "prompt_hash": combined_hash,
        "system_hash": system_hash,
        "user_hash": user_hash,
        "system_file": system_file.name,
        "user_file": user_file.name,
    }
    _save_meta(meta)

    print(f"  EXPORTED: {version}")
    print(f"    system: {system_file.name} ({len(SYSTEM_PROMPT_V4):,} chars)")
    print(f"    user:   {user_file.name} ({len(BRIEFING_REPORT_PROMPT_V4):,} chars)")
    print(f"    hash:   {combined_hash}")
    print(f"    commit: {regscan_commit}")
    return True


def main():
    parser = argparse.ArgumentParser(description="RegScan 프롬프트 추출기")
    parser.add_argument(
        "--version",
        type=str,
        default="v4.0",
        help="버전 라벨 (기본: v4.0)",
    )
    parser.add_argument(
        "--regscan-dir",
        type=str,
        default=str(DEFAULT_REGSCAN_DIR),
        help=f"RegScan 루트 디렉터리 (기본: {DEFAULT_REGSCAN_DIR})",
    )
    args = parser.parse_args()

    regscan_dir = Path(args.regscan_dir)
    if not (regscan_dir / "regscan" / "report" / "prompts.py").exists():
        print(f"ERROR: prompts.py를 찾을 수 없음: {regscan_dir}")
        sys.exit(1)

    print(f"\nRegScan 프롬프트 추출 → evals/regscan/prompts/")
    print(f"  version:    {args.version}")
    print(f"  regscan:    {regscan_dir}")
    print()

    changed = export_prompts(args.version, regscan_dir)
    if changed:
        print(f"\n완료. 'npx promptfoo eval' 로 평가를 실행하세요.")
    else:
        print(f"\n변경 없음. 프롬프트가 동일합니다.")


if __name__ == "__main__":
    main()
