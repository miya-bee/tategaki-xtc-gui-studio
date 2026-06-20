from __future__ import annotations

from pathlib import Path


def test_draw_text_run_paths_use_shared_action_resolver() -> None:
    source = Path('tategakiXTC_gui_core_renderer.py').read_text(encoding='utf-8')

    assert 'def _resolve_vertical_layout_action(' in source
    assert source.count('action = _resolve_vertical_layout_action(') == 1
    assert 'action = choose_layout_action(' not in source
    assert 'choose_layout_action = _choose_vertical_layout_action_with_hints' not in source
    assert 'def _run_vertical_text_cells(' in source


def test_non_cached_kinsoku_wrapper_has_no_duplicate_rule_tree() -> None:
    source = Path('tategakiXTC_gui_core_renderer.py').read_text(encoding='utf-8')
    start = source.index('def _choose_vertical_layout_action(tokens: Sequence[str]')
    end = source.index('\n\n@lru_cache(maxsize=128)\ndef _double_punctuation_layout', start)
    body = source[start:end]

    assert '_build_vertical_layout_hints(tokens)' in body
    assert '_choose_vertical_layout_action_with_hints(' in body
    assert '_protected_token_group_length(tokens, idx)' not in body
    assert '_would_orphan_short_tail_after_break(tokens, idx)' not in body
