import pytest

from foodlog import replies
from foodlog.analysis import Analysis
from foodlog.config import ConfigError, load_config


def write_env(tmp_path, **over):
    values = {
        "DISCORD_TOKEN": "tok",
        "CHANNEL_ID": "123",
        "CLAUDE_MODEL": "sonnet",
        "DATA_DIR": str(tmp_path / "data"),
        **over,
    }
    env = tmp_path / ".env"
    env.write_text("\n".join(f"{k}={v}" for k, v in values.items()), encoding="utf-8")
    return env


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in ("DISCORD_TOKEN", "CHANNEL_ID", "CLAUDE_MODEL", "DATA_DIR"):
        monkeypatch.delenv(key, raising=False)


def test_load_ok_creates_photos_dir(tmp_path):
    cfg = load_config(write_env(tmp_path))
    assert cfg.channel_id == 123 and cfg.photos_dir.is_dir()


def test_relative_data_dir_is_anchored_to_the_project_folder(tmp_path, monkeypatch):
    from foodlog import config as config_module

    project = tmp_path / "project"
    project.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr(config_module, "REPO_ROOT", project)
    monkeypatch.chdir(elsewhere)
    cfg = load_config(write_env(tmp_path, DATA_DIR="data"))
    assert cfg.data_dir == (project / "data").resolve()


def test_missing_values_are_reported_in_plain_words(tmp_path):
    with pytest.raises(ConfigError, match="DISCORD_TOKEN"):
        load_config(write_env(tmp_path, DISCORD_TOKEN=""))


def test_channel_id_must_be_a_number(tmp_path):
    with pytest.raises(ConfigError, match="CHANNEL_ID"):
        load_config(write_env(tmp_path, CHANNEL_ID="abc"))


def test_food_reply_has_everything_required():
    a = Analysis(True, "雞腿便當", ("白飯", "雞腿"), 650, 920)
    text = replies.food_reply("<@1>", a, 1480)
    for part in ("雞腿便當", "白飯、雞腿", "650", "920", "當日已攝取熱量", "1,480"):
        assert part in text


def test_not_food_reply_still_shows_daily_total():
    a = Analysis(False, "馬克杯", (), 0, 0)
    text = replies.not_food_reply("<@1>", a, 1480)
    assert "不是食物，是馬克杯" in text and "1,480" in text


def test_ai_text_cannot_ping_everyone():
    a = Analysis(True, "@everyone 來吃", ("@here",), 100, 100)
    text = replies.food_reply("<@1>", a, 100)
    assert "@everyone" not in text and "@here" not in text


def test_long_reply_is_trimmed():
    a = Analysis(True, "x", tuple("y" * 30 for _ in range(15)), 1, 1)
    assert len(replies.food_reply("<@1>", a, 1)) <= replies.DISCORD_LIMIT
