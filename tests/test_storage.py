from datetime import datetime

import pytest

from foodlog.storage import build_stem, detect_image_ext, save_photo

WHEN = datetime(2026, 10, 20, 14, 30, 5)
PREFIX = "2026-10-20 14-30-05 "


def test_detect_image_ext():
    assert detect_image_ext(b"\xff\xd8\xff\xe0abc") == "jpg"
    assert detect_image_ext(b"\x89PNG\r\n\x1a\nxxxx") == "png"
    assert detect_image_ext(b"GIF89a....") == "gif"
    assert detect_image_ext(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "webp"
    assert detect_image_ext(b"%PDF-1.7") is None
    assert detect_image_ext(b"") is None


def test_filename_format(tmp_path):
    path = save_photo(tmp_path, WHEN, "雞腿便當", "jpg", b"x")
    assert path.name == "2026-10-20 14-30-05 雞腿便當.jpg"
    assert path.read_bytes() == b"x"


def test_same_second_collisions_get_suffix(tmp_path):
    names = [save_photo(tmp_path, WHEN, "拉麵", "png", bytes([i])).name for i in range(3)]
    assert names == [
        "2026-10-20 14-30-05 拉麵.png",
        "2026-10-20 14-30-05 拉麵-2.png",
        "2026-10-20 14-30-05 拉麵-3.png",
    ]
    assert (tmp_path / names[0]).read_bytes() == b"\x00"  # 沒有被覆蓋


HOSTILE = [
    "../../evil", "..\\..\\evil", "a/b", "a\\b", "C:\\x", "C:x", "....", "..", ".", "/", "\\",
    "CON", "nul", "com1", "a:b:c", 'a*b?"c<d>e|f', "line1\nline2\ttab", "\x00\x01",
    "／＼：", "../" * 50, "x" * 500, "", "   ", "=cmd|' /C calc'!A0", "evil.exe ", " .hidden",
]


@pytest.mark.parametrize("raw", HOSTILE)
def test_protection_3_hostile_names_stay_inside_photos(tmp_path, raw):
    photos = tmp_path / "photos"
    photos.mkdir()
    path = save_photo(photos, WHEN, raw, "jpg", b"x")
    assert path.resolve().parent == photos.resolve()
    assert not any(ch in path.name[len(PREFIX):] for ch in '/\\:*?"<>|')
    assert ".." not in path.name
    assert [p.name for p in tmp_path.iterdir()] == ["photos"], "不能有任何檔案跑到 photos 之外"


def test_protection_3_stem_values(tmp_path):
    def f(raw):
        return build_stem(raw, tmp_path, "2026-10-20 14-30-05", "jpg")

    assert f("../../evil") == "evil"
    assert f("") == "未命名"
    assert f("CON") == "CON_"
    assert f("雞腿 便當") == "雞腿_便當"
    assert len(f("x" * 500)) == 20
