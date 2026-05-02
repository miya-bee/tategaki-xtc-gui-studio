from __future__ import annotations

from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / 'tests' / 'golden_images'

# Golden image naming conventions:
# - glyph_*: single-glyph comparisons with strict thresholds
# - tatechuyoko_*: compact vertical-in-horizontal samples
# - page_*: full-page or multi-page layout regressions
#
# Threshold profiles should use the same family prefix as the case name.
# tests/test_golden_profile_registry.py enforces this relationship.

THRESHOLD_PROFILES = {
    'glyph_strict': {'threshold_ratio': 0.0015, 'threshold_mean': 0.20},
    'tatechuyoko_strict': {'threshold_ratio': 0.0020, 'threshold_mean': 0.30},
    'page_compound_standard': {'threshold_ratio': 0.0060, 'threshold_mean': 0.70},
    'page_heading_standard': {'threshold_ratio': 0.0060, 'threshold_mean': 0.80},
    'page_punctuation_dense': {'threshold_ratio': 0.0080, 'threshold_mean': 1.20},
    'page_device_profile': {'threshold_ratio': 0.0040, 'threshold_mean': 0.50},
    'page_ruby_columns': {'threshold_ratio': 0.0080, 'threshold_mean': 1.20},
    'page_ruby_pages': {'threshold_ratio': 0.0100, 'threshold_mean': 1.30},
    'page_output_filter': {'threshold_ratio': 0.0100, 'threshold_mean': 1.50},
    'page_ruby_extreme': {'threshold_ratio': 0.0080, 'threshold_mean': 1.10},
}

CASE_PROFILE_PREFIX_RULES = {
    'glyph_': 'glyph_',
    'tatechuyoko_': 'tatechuyoko_',
    'page_': 'page_',
}


def expected_profile_prefix_for_case(case_name: str) -> str:
    for case_prefix, profile_prefix in CASE_PROFILE_PREFIX_RULES.items():
        if case_name.startswith(case_prefix):
            return profile_prefix
    return ''


def validate_threshold_profile_registry(case_specs: Dict[str, Dict], threshold_profiles: Dict[str, Dict[str, float]]) -> Dict[str, List[str]]:
    referenced = []
    missing = []
    mismatched = []
    for case_name, spec in case_specs.items():
        profile_name = spec.get('threshold_profile')
        if not profile_name:
            continue
        referenced.append(profile_name)
        if profile_name not in threshold_profiles:
            missing.append(case_name)
            continue
        expected_prefix = expected_profile_prefix_for_case(case_name)
        if expected_prefix and not str(profile_name).startswith(expected_prefix):
            mismatched.append(case_name)
    unused = sorted(name for name in threshold_profiles if name not in set(referenced))
    return {
        'referenced_profiles': sorted(set(referenced)),
        'missing_profile_cases': sorted(missing),
        'unused_profiles': unused,
        'family_mismatch_cases': sorted(mismatched),
    }


def resolve_case_thresholds(spec: Dict) -> Dict[str, float]:
    profile_name = spec.get('threshold_profile')
    base = {}
    if profile_name:
        profile = THRESHOLD_PROFILES.get(profile_name)
        if profile is None:
            raise KeyError(f"Unknown threshold profile: {profile_name!r}")
        base = dict(profile)
    if 'threshold_ratio' in spec:
        base['threshold_ratio'] = float(spec['threshold_ratio'])
    if 'threshold_mean' in spec:
        base['threshold_mean'] = float(spec['threshold_mean'])
    if 'threshold_ratio' not in base or 'threshold_mean' not in base:
        raise KeyError(f"Golden case threshold is incomplete: {spec!r}")
    return {
        'threshold_ratio': float(base['threshold_ratio']),
        'threshold_mean': float(base['threshold_mean']),
    }


CASE_SPECS = {
    'glyph_ichi': {
        'kind': 'glyph',
        'char': '一',
        'font_size': 48,
        'canvas_size': 96,
        'origin': (24, 24),
        'threshold_profile': 'glyph_strict',
    },

    'glyph_small_kana_ya': {
        'kind': 'glyph',
        'char': 'ゃ',
        'font_size': 48,
        'canvas_size': 96,
        'origin': (24, 24),
        'threshold_profile': 'glyph_strict',
    },
    'glyph_chouon': {
        'kind': 'glyph',
        'char': 'ー',
        'font_size': 48,
        'canvas_size': 96,
        'origin': (24, 24),
        'threshold_profile': 'glyph_strict',
    },
    'tatechuyoko_2025': {
        'kind': 'tatechuyoko',
        'text': '2025',
        'font_size': 48,
        'canvas_size': 96,
        'origin': (24, 24),
        'threshold_profile': 'tatechuyoko_strict',
    },
    'page_compound_layout': {
        'kind': 'page_blocks',
        'args': {
            'width': 160,
            'height': 220,
            'font_size': 28,
            'ruby_size': 14,
            'margin_l': 18,
            'margin_r': 12,
            'margin_t': 12,
            'margin_b': 12,
            'line_spacing': 38,
            'output_format': 'xtc',
        },
        'blocks': [
            {
                'kind': 'paragraph',
                'runs': [
                    {'text': '吾輩', 'ruby': 'わがはい', 'bold': False},
                    {'text': 'は2025年のAI、', 'ruby': '', 'bold': False},
                    {'text': '「一ー」', 'ruby': '', 'bold': False},
                    {'text': 'である。', 'ruby': '', 'bold': False},
                ],
            }
        ],
        'page_mode': 'first',
        'threshold_profile': 'page_compound_standard',
    },
    'page_heading_spacing': {
        'kind': 'page_blocks',
        'args': {
            'width': 180,
            'height': 280,
            'font_size': 28,
            'ruby_size': 14,
            'margin_l': 18,
            'margin_r': 12,
            'margin_t': 12,
            'margin_b': 12,
            'line_spacing': 38,
            'output_format': 'xtc',
        },
        'blocks': [
            {
                'kind': 'heading',
                'runs': [
                    {'text': '第一章', 'ruby': '', 'bold': False},
                ],
                'indent': False,
                'blank_before': 2,
            },
            {
                'kind': 'paragraph',
                'runs': [
                    {'text': 'これは見出しのあとに続く本文です。', 'ruby': '', 'bold': False},
                ],
                'indent': False,
                'blank_before': 1,
            },
        ],
        'page_mode': 'first',
        'threshold_profile': 'page_heading_standard',
    },

    'page_closing_bracket_period': {
        'kind': 'page_blocks',
        'args': {
            'width': 140,
            'height': 220,
            'font_size': 28,
            'ruby_size': 14,
            'margin_l': 18,
            'margin_r': 12,
            'margin_t': 12,
            'margin_b': 12,
            'line_spacing': 38,
            'output_format': 'xtc',
        },
        'blocks': [
            {
                'kind': 'paragraph',
                'runs': [
                    {'text': '」。」』。」』。、', 'ruby': '', 'bold': False},
                ],
                'indent': False,
                'blank_before': 1,
            },
        ],
        'page_mode': 'strip',
        'gap': 6,
        'threshold_profile': 'page_punctuation_dense',
    },
    'page_consecutive_punctuation': {
        'kind': 'page_blocks',
        'args': {
            'width': 140,
            'height': 220,
            'font_size': 28,
            'ruby_size': 14,
            'margin_l': 18,
            'margin_r': 12,
            'margin_t': 12,
            'margin_b': 12,
            'line_spacing': 38,
            'output_format': 'xtc',
        },
        'blocks': [
            {
                'kind': 'paragraph',
                'runs': [
                    {'text': '「こんにちは」、と彼は言った。』『』。。', 'ruby': '', 'bold': False},
                ],
                'indent': False,
                'blank_before': 1,
            },
        ],
        'page_mode': 'strip',
        'gap': 6,
        'threshold_profile': 'page_punctuation_dense',
    },

    'page_x4_profile_layout': {
        'kind': 'page_blocks',
        'args': {
            'width': 480,
            'height': 800,
            'font_size': 36,
            'ruby_size': 18,
            'margin_l': 24,
            'margin_r': 24,
            'margin_t': 24,
            'margin_b': 24,
            'line_spacing': 48,
            'output_format': 'xtc',
        },
        'blocks': [
            {
                'kind': 'heading',
                'runs': [
                    {'text': 'X4 確認', 'ruby': '', 'bold': False},
                ],
                'indent': False,
                'blank_before': 1,
            },
            {
                'kind': 'paragraph',
                'runs': [
                    {'text': '吾輩', 'ruby': 'わがはい', 'bold': False},
                    {'text': 'は猫である。2025年のAIでも、', 'ruby': '', 'bold': False},
                    {'text': '「一ー」', 'ruby': '', 'bold': False},
                    {'text': 'の位置を確認する。', 'ruby': '', 'bold': False},
                ],
                'indent': False,
                'blank_before': 1,
            },
        ],
        'page_mode': 'first',
        'threshold_profile': 'page_device_profile',
    },
    'page_x3_profile_layout': {
        'kind': 'page_blocks',
        'args': {
            'width': 528,
            'height': 792,
            'font_size': 34,
            'ruby_size': 17,
            'margin_l': 24,
            'margin_r': 24,
            'margin_t': 24,
            'margin_b': 24,
            'line_spacing': 44,
            'output_format': 'xtc',
        },
        'blocks': [
            {
                'kind': 'heading',
                'runs': [
                    {'text': 'X3 確認', 'ruby': '', 'bold': False},
                ],
                'indent': False,
                'blank_before': 1,
            },
            {
                'kind': 'paragraph',
                'runs': [
                    {'text': '吾輩', 'ruby': 'わがはい', 'bold': False},
                    {'text': 'は猫である。2025年のAIでも、', 'ruby': '', 'bold': False},
                    {'text': '「一ー」', 'ruby': '', 'bold': False},
                    {'text': 'の位置を確認する。', 'ruby': '', 'bold': False},
                ],
                'indent': False,
                'blank_before': 1,
            },
        ],
        'page_mode': 'first',
        'threshold_profile': 'page_device_profile',
    },
    'ruby_across_columns_layout': {
        'kind': 'page_blocks',
        'args': {
            'width': 160,
            'height': 220,
            'font_size': 24,
            'ruby_size': 12,
            'margin_l': 8,
            'margin_r': 8,
            'margin_t': 8,
            'margin_b': 8,
            'line_spacing': 32,
            'output_format': 'xtc',
        },
        'blocks': [
            {
                'kind': 'paragraph',
                'runs': [
                    {
                        'text': '吾輩は猫である吾輩は猫である吾輩は猫である吾輩は猫である',
                        'ruby': 'わがはいはねこであるわがはいはねこであるわがはいはねこであるわがはいはねこである',
                        'bold': False,
                    },
                ],
                'indent': False,
                'blank_before': 1,
            },
        ],
        'page_mode': 'first',
        'threshold_profile': 'page_ruby_columns',
    },
    'ruby_across_pages_layout': {
        'kind': 'page_blocks',
        'args': {
            'width': 120,
            'height': 120,
            'font_size': 24,
            'ruby_size': 12,
            'margin_l': 8,
            'margin_r': 8,
            'margin_t': 8,
            'margin_b': 8,
            'line_spacing': 32,
            'output_format': 'xtc',
        },
        'blocks': [
            {
                'kind': 'paragraph',
                'runs': [
                    {
                        'text': '吾輩は猫である吾輩は猫である吾輩は猫である吾輩は猫である',
                        'ruby': 'わがはいはねこであるわがはいはねこであるわがはいはねこであるわがはいはねこである',
                        'bold': False,
                    },
                ],
                'indent': False,
                'blank_before': 1,
            },
        ],
        'page_mode': 'strip',
        'gap': 6,
        'threshold_profile': 'page_ruby_pages',
    },
    'page_night_mode_layout': {
        'kind': 'filtered_page',
        'args': {
            'width': 180,
            'height': 240,
            'font_size': 28,
            'ruby_size': 14,
            'margin_l': 18,
            'margin_r': 12,
            'margin_t': 12,
            'margin_b': 12,
            'line_spacing': 38,
            'threshold': 128,
            'dither': False,
            'night_mode': True,
            'output_format': 'xtc',
        },
        'blocks': [
            {
                'kind': 'paragraph',
                'runs': [
                    {'text': '夜間表示で吾輩', 'ruby': 'やかんひょうじでわがはい', 'bold': False},
                    {'text': 'は猫である。', 'ruby': '', 'bold': False},
                ],
                'indent': False,
                'blank_before': 1,
            },
        ],
        'page_mode': 'first',
        'threshold_profile': 'page_output_filter',
    },
    'page_xtch_filter_layout': {
        'kind': 'filtered_page',
        'args': {
            'width': 180,
            'height': 240,
            'font_size': 28,
            'ruby_size': 14,
            'margin_l': 18,
            'margin_r': 12,
            'margin_t': 12,
            'margin_b': 12,
            'line_spacing': 38,
            'threshold': 120,
            'dither': False,
            'night_mode': False,
            'output_format': 'xtch',
        },
        'blocks': [
            {
                'kind': 'paragraph',
                'runs': [
                    {'text': '四階調の吾輩', 'ruby': 'よんかいちょうのわがはい', 'bold': False},
                    {'text': 'は猫である。', 'ruby': '', 'bold': False},
                ],
                'indent': False,
                'blank_before': 1,
            },
        ],
        'page_mode': 'first',
        'threshold_profile': 'page_output_filter',
    },
    'page_ruby_size_small_layout': {
        'kind': 'page_blocks',
        'args': {
            'width': 180,
            'height': 240,
            'font_size': 28,
            'ruby_size': 10,
            'margin_l': 18,
            'margin_r': 12,
            'margin_t': 12,
            'margin_b': 12,
            'line_spacing': 38,
            'output_format': 'xtc',
        },
        'blocks': [
            {
                'kind': 'paragraph',
                'runs': [
                    {'text': '吾輩', 'ruby': 'わがはい', 'bold': False},
                    {'text': 'の小さなルビを確認する。', 'ruby': '', 'bold': False},
                ],
                'indent': False,
                'blank_before': 1,
            },
        ],
        'page_mode': 'first',
        'threshold_profile': 'page_ruby_extreme',
    },
    'page_ruby_size_large_layout': {
        'kind': 'page_blocks',
        'args': {
            'width': 180,
            'height': 260,
            'font_size': 28,
            'ruby_size': 22,
            'margin_l': 18,
            'margin_r': 12,
            'margin_t': 12,
            'margin_b': 12,
            'line_spacing': 42,
            'output_format': 'xtc',
        },
        'blocks': [
            {
                'kind': 'paragraph',
                'runs': [
                    {'text': '吾輩', 'ruby': 'わがはい', 'bold': False},
                    {'text': 'の大きなルビを確認する。', 'ruby': '', 'bold': False},
                ],
                'indent': False,
                'blank_before': 1,
            },
        ],
        'page_mode': 'first',
        'threshold_profile': 'page_ruby_extreme',
    },
}

