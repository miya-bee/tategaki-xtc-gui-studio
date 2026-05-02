"""回帰用ゴールデン画像の確認・更新スクリプト。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.golden_regression_tools import (
    check_all_cases,
    check_cases,
    describe_golden_case_scope,
    describe_reference_font_action_hint,
    describe_reference_font_skip_hint,
    describe_reference_font_status,
    describe_reference_font_status_line,
    describe_reference_font_next_check,
    describe_skipped_case_names,
    describe_skipped_case_summary,
    describe_stale_case_names,
    describe_stale_case_summary,
    format_golden_check_command,
    format_golden_check_command_block,
    format_golden_update_command,
    format_golden_update_command_block,
    golden_path,
    normalize_case_names,
    skipped_case_names,
    stale_case_names,
    stale_case_results,
    summarize_result,
    update_all_stale_cases,
    update_stale_case_results,
    update_stale_cases,
)


def main() -> int:
    parser = argparse.ArgumentParser(description='ゴールデン画像の確認・更新を行います。')
    parser.add_argument('--check', action='store_true', help='差分確認のみ行い、更新しません。')
    parser.add_argument('--update', action='store_true', help='差分があるゴールデン画像だけ更新します。')
    parser.add_argument('--list', action='store_true', help='全ケース名を表示します。')
    parser.add_argument('--list-stale', action='store_true', help='差分があるケース名だけを表示します。更新はしません。')
    parser.add_argument('--font-status', action='store_true', help='ゴールデン比較用の基準フォント配置状態を表示します。')
    parser.add_argument('--case', action='append', default=[], help='対象ケース名を1件に絞ります。複数指定できます。')
    args = parser.parse_args()

    try:
        case_names = normalize_case_names(args.case)
    except KeyError as exc:
        parser.error(str(exc).strip("'"))

    if args.list:
        for name in case_names:
            print(name)
        return 0

    if args.font_status:
        print(describe_golden_case_scope(args.case))
        print(describe_reference_font_status())
        print(describe_reference_font_action_hint())
        print(describe_reference_font_next_check(args.case))
        return 0

    results = check_cases(case_names)

    if args.check or args.update or args.list_stale:
        print(describe_golden_case_scope(args.case))
        print(describe_reference_font_status_line())

    skipped = [result for result in results if result.get('skipped')]
    skipped_names = skipped_case_names(results)
    stale = stale_case_results(results)

    if args.list_stale:
        if skipped and len(skipped) == len(results):
            print(describe_skipped_case_summary(skipped_names))
            print(describe_skipped_case_names(skipped_names))
            print('同梱基準フォントが無いためゴールデン比較を省略しました。')
            print(describe_reference_font_skip_hint())
            return 0
        if skipped_names:
            print(describe_skipped_case_summary(skipped_names))
            print(describe_skipped_case_names(skipped_names))
        names = stale_case_names(results)
        print(describe_stale_case_summary(names))
        print(describe_stale_case_names(names))
        for name in names:
            print(name)
        if names:
            print(f'確認するには: {format_golden_check_command(names)}')
            print('確認コマンド:')
            print(format_golden_check_command_block(names))
            print(f'更新するには: {format_golden_update_command(names)}')
            print('更新コマンド:')
            print(format_golden_update_command_block(names))
            return 1
        print('差分ケースはありません。')
        return 0
    if args.check:
        if skipped and len(skipped) == len(results):
            print(describe_skipped_case_summary(skipped_names))
            print(describe_skipped_case_names(skipped_names))
            print('同梱基準フォントが無いためゴールデン比較を省略しました。')
            print(describe_reference_font_skip_hint())
            return 0
        if skipped_names:
            print(describe_skipped_case_summary(skipped_names))
            print(describe_skipped_case_names(skipped_names))
        if stale:
            for result in stale:
                print(summarize_result(result))
            names = stale_case_names(stale)
            print(f'差分があります。更新するには: {format_golden_update_command(names)}')
            print('更新コマンド:')
            print(format_golden_update_command_block(names))
            return 1
        if skipped_names:
            print('比較可能なゴールデン画像は最新です。')
        else:
            print('ゴールデン画像は最新です。')
        return 0

    if args.update:
        if skipped and len(skipped) == len(results):
            print(describe_skipped_case_summary(skipped_names))
            print(describe_skipped_case_names(skipped_names))
            print('同梱基準フォントが無いためゴールデン比較を省略しました。')
            print(describe_reference_font_skip_hint())
            return 0
        if skipped_names:
            print(describe_skipped_case_summary(skipped_names))
            print(describe_skipped_case_names(skipped_names))
        updated = update_stale_case_results(results)
        if updated:
            updated_names = stale_case_names(results)
            for path in updated:
                print(f'updated: {path}')
            print(f'確認するには: {format_golden_check_command(updated_names)}')
            print('確認コマンド:')
            print(format_golden_check_command_block(updated_names))
        elif skipped_names:
            print('比較可能なゴールデン画像に更新対象はありません。')
        else:
            print('更新の必要はありません。')
        return 0

    # 互換動作: 引数なしは全ケースを再生成
    if skipped and len(skipped) == len(results):
        print(describe_skipped_case_summary(skipped_names))
        print(describe_skipped_case_names(skipped_names))
        print('同梱基準フォントが無いためゴールデン比較を省略しました。')
        print(describe_reference_font_skip_hint())
        return 0
    for result in results:
        if result.get('skipped'):
            print(summarize_result(result))
            continue
        path = golden_path(str(result['name']))
        result['actual'].save(path)
        print(f'generated: {path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
