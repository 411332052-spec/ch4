from pathlib import Path

import pytest

from foodlog.config import Config


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    data_dir = tmp_path / "data"
    (data_dir / "photos").mkdir(parents=True)
    return Config(discord_token="x", channel_id=1, claude_model="sonnet", data_dir=data_dir)
