"""四段防護的開始／結束註解都在，而且成對、格式固定（之後教學要靠它逐段開關）。"""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "foodlog"
START = re.compile(r"^\s*# ==== 防護 (\d)：.+　開始 ====$")
END = re.compile(r"^\s*# ==== 防護 (\d) 結束 ====$")


def find_sections():
    found: dict[int, list[tuple[str, int, int]]] = {}
    for path in sorted(SRC.glob("*.py")):
        open_at = None
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if m := START.match(line):
                assert open_at is None, f"{path.name}:{lineno} 防護段落沒有先結束就又開始"
                open_at = (int(m[1]), lineno)
            elif m := END.match(line):
                assert open_at and open_at[0] == int(m[1]), f"{path.name}:{lineno} 結束標記沒有對應的開始"
                found.setdefault(open_at[0], []).append((path.name, open_at[1], lineno))
                open_at = None
        assert open_at is None, f"{path.name} 防護 {open_at[0]} 沒有結束標記"
    return found


def test_all_four_protections_exist_exactly_once():
    found = find_sections()
    assert sorted(found) == [1, 2, 3, 4]
    assert all(len(v) == 1 for v in found.values())


def test_sections_are_active_not_commented_out():
    for sections in find_sections().values():
        for name, start, end in sections:
            body = (SRC / name).read_text(encoding="utf-8").splitlines()[start:end - 1]
            code = [line for line in body if line.strip() and not line.strip().startswith("#")]
            assert code, f"{name} 第 {start} 行那一段是空的或被整段註解掉了"
