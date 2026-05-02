from PIL import ImageChops, ImageStat

from tests.image_golden_cases import render_case


def test_night_mode_filtered_case_inverts_background() -> None:
    img = render_case('page_night_mode_layout').convert('L')
    # Night mode should produce a dark background near the page edge.
    assert img.getpixel((0, 0)) < 16


def test_xtch_filtered_case_contains_multiple_gray_levels() -> None:
    img = render_case('page_xtch_filter_layout').convert('L')
    values = [index for index, count in enumerate(img.histogram()) if count]
    assert len(values) >= 4
    assert values[0] == 0
    assert values[-1] == 255


def test_ruby_size_extreme_cases_produce_distinct_layouts() -> None:
    small = render_case('page_ruby_size_small_layout').convert('L')
    large = render_case('page_ruby_size_large_layout').convert('L')
    diff = ImageChops.difference(small, large)
    assert diff.getbbox() is not None
    assert ImageStat.Stat(diff).mean[0] > 0.5
