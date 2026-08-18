#!/usr/bin/env python3
"""CLI entry point for the newsletter automation system."""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables before importing other modules
load_dotenv()


def get_next_wednesday() -> str:
    """Get the date of the next Wednesday."""
    today = datetime.now()
    days_until_wednesday = (2 - today.weekday()) % 7
    if days_until_wednesday == 0 and today.hour >= 12:
        days_until_wednesday = 7
    next_wed = today + timedelta(days=days_until_wednesday)
    return next_wed.strftime("%Y-%m-%d")


def validate_topic_count(count: int, topics: str | None) -> int:
    """Return the number of slots left for candidate selection."""
    named = len([t for t in (topics or "").split(",") if t.strip()])
    if count < named:
        raise ValueError(f"--count({count})가 --topics 개수({named})보다 작습니다. --count를 늘리세요.")
    return count - named


def count_articles(target_date: str) -> int:
    """Article files actually written, excluding generated non-articles."""
    skip = {"newsletter.md", "research_results.md"}
    return len([p for p in Path(f"articles/{target_date}").glob("*.md") if p.name not in skip])


def main():
    parser = argparse.ArgumentParser(
        description="오토마타 뉴스레터 자동화 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python run.py                                    # 다음 수요일 발행용, 아티클 4개
  python run.py --hitl                             # 토픽을 직접 선택
  python run.py --topics "X, Y" --count 4 --hitl   # X, Y 조사 + 후보에서 2개 선택
  python run.py --refresh                          # 리서치 캐시 무시하고 재수집
  python run.py --preview 2026-01-15               # 기존 아티클 미리보기
        """,
    )

    parser.add_argument(
        "--date", "-d",
        type=str,
        help="뉴스레터 발행일 (YYYY-MM-DD 형식, 기본값: 다음 수요일)",
    )

    parser.add_argument(
        "--preview", "-p",
        type=str,
        metavar="DATE_DIR",
        help="기존 아티클 미리보기 (날짜 디렉토리 지정)",
    )

    parser.add_argument(
        "--merge", "-m",
        type=str,
        metavar="DATE_DIR",
        help="기존 아티클 병합만 수행 (날짜 디렉토리 지정)",
    )

    parser.add_argument(
        "--version", "-v",
        type=str,
        help="뉴스레터 버전 번호 (병합 시 사용)",
    )

    parser.add_argument(
        "--hitl",
        action="store_true",
        help="Human-in-the-loop 모드 활성화 (토픽 선정 시 승인 필요)",
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="빠른 테스트 모드 (아티클 1개만 생성)",
    )

    parser.add_argument(
        "--topics", "-t",
        type=str,
        default=None,
        help="반드시 포함할 토픽 목록 (쉼표로 구분, 예: 'Claude 4 출시, RAG 개선')",
    )

    parser.add_argument(
        "--count", "-c",
        type=int,
        default=4,
        help="뉴스레터에 포함할 총 아티클 수 (기본값: 4)",
    )

    parser.add_argument(
        "--refresh",
        action="store_true",
        help="캐시된 리서치 후보를 버리고 다시 수집",
    )

    args = parser.parse_args()

    # Preview mode
    if args.preview:
        from src.utils.merge_articles import preview_newsletter
        print(preview_newsletter(args.preview))
        return 0

    # Merge only mode
    if args.merge:
        from src.utils.merge_articles import merge_newsletter
        try:
            output_path = merge_newsletter(args.merge, version=args.version)
            print(f"뉴스레터가 생성되었습니다: {output_path}")
            return 0
        except Exception as e:
            print(f"오류: {e}", file=sys.stderr)
            return 1

    # Full generation mode
    target_date = args.date or get_next_wednesday()

    try:
        open_slots = validate_topic_count(args.count, args.topics)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    if args.refresh:
        Path(f"artifacts/research/{target_date}/candidates.json").unlink(missing_ok=True)
        print("🔄 캐시된 리서치 후보를 삭제했습니다")

    print(f"🚀 오토마타 뉴스레터 생성 시작")
    print(f"📅 발행 예정일: {target_date}")
    print(f"📝 아티클 {args.count}개 (지정 {args.count - open_slots}개 + 후보 선택 {open_slots}개)")
    print("-" * 40)

    if args.quick:
        from src.main import run_quick_test
        run_func = run_quick_test
        print("⚡ 빠른 테스트 모드 (아티클 1개만 생성)")
    else:
        from src.main import run_newsletter_generation
        run_func = run_newsletter_generation

    try:
        result = run_func(target_date, use_hitl=args.hitl, user_topics=args.topics, count=args.count)
        print("-" * 40)
        if result is None:
            print("❌ 뉴스레터 생성 실패")
            return 1

        expected = 1 if args.quick else args.count   # quick mode forces a single article
        written = count_articles(target_date)
        if written < expected:
            print(f"❌ 아티클 {expected}개 중 {written}개만 생성되었습니다", file=sys.stderr)
            print(f"📁 부분 결과: articles/{target_date}/", file=sys.stderr)
            return 1

        print("✅ 뉴스레터 생성 완료!")
        print(f"📁 결과 위치: articles/{target_date}/")
        return 0
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단되었습니다.")
        return 130
    except Exception as e:
        print(f"❌ 오류 발생: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
