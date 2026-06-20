from __future__ import annotations

import random

import tategakiXTC_gui_core as core


_TOKEN_POOL = tuple('吾輩は猫である。名前はまだ無い「」！？、。・一ABCDE123') + (
    '!?',
    '??',
    '!!',
    '?!',
)


def test_non_cached_vertical_layout_decider_delegates_to_hinted_decider() -> None:
    tokens = tuple('「吾輩は猫である。」!?')
    hints = core._build_vertical_layout_hints(tokens)

    assert core._choose_vertical_layout_action(tokens, 0, 12, 12, 1448, 14, 26, 'standard') == core._choose_vertical_layout_action_with_hints(
        hints,
        0,
        core._remaining_vertical_slots(12, 1448, 14, 26),
        False,
        'standard',
    )


def test_cached_and_non_cached_kinsoku_deciders_match_for_random_inputs() -> None:
    rng = random.Random(150024)
    cases_checked = 0
    modes = ('off', 'simple', 'standard', 'unknown')
    for _ in range(100_000):
        token_count = rng.randint(1, 24)
        tokens = tuple(rng.choice(_TOKEN_POOL) for _ in range(token_count))
        hints = core._build_vertical_layout_hints(tokens)
        idx = rng.randrange(token_count)
        margin_t = rng.choice((0, 4, 12, 24, 48))
        margin_b = rng.choice((0, 8, 14, 32))
        font_size = rng.choice((12, 18, 26, 34, 42))
        height = rng.choice((96, 160, 320, 792, 1448))
        step = font_size + 2
        curr_y = margin_t + rng.randint(0, 12) * step
        mode = rng.choice(modes)

        slots_left = core._remaining_vertical_slots(curr_y, height, margin_b, font_size)
        expected = core._choose_vertical_layout_action_with_hints(
            hints,
            idx,
            slots_left,
            core._is_after_effective_column_top(curr_y, margin_t),
            kinsoku_mode=mode,
        )
        actual = core._choose_vertical_layout_action(
            tokens,
            idx,
            curr_y,
            margin_t,
            height,
            margin_b,
            font_size,
            kinsoku_mode=mode,
        )
        assert actual == expected
        cases_checked += 1

    assert cases_checked == 100_000
