"""data.json 來源外掛測試。"""

from __future__ import annotations

from app.config import DataConfig
from app.io.data_source import (
    LocalDataSource,
    RemoteDataSource,
    build_data_source,
)


def _cfg() -> DataConfig:
    return DataConfig(local="data/data.json")


def test_raw_url_format() -> None:
    cfg = DataConfig()
    assert cfg.raw_url == (
        "https://raw.githubusercontent.com/"
        "normalsky315-jpg/NKUinfos/main/data.json"
    )


def test_factory_selects_source_type() -> None:
    cfg = _cfg()
    assert isinstance(build_data_source("local", cfg), LocalDataSource)
    assert isinstance(build_data_source("github", cfg), RemoteDataSource)
    assert isinstance(
        build_data_source("https://example.com/data.json", cfg), RemoteDataSource
    )
    assert isinstance(build_data_source("some/path.json", cfg), LocalDataSource)


def test_factory_github_uses_raw_url() -> None:
    source = build_data_source("github", _cfg())
    assert isinstance(source, RemoteDataSource)
    assert source.url == _cfg().raw_url


def test_local_source_loads_projects() -> None:
    data = LocalDataSource("data/data.json").load()
    assert "projects" in data and len(data["projects"]) > 0


def test_remote_falls_back_to_local(monkeypatch) -> None:
    def _boom(*_args, **_kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("requests.get", _boom)
    source = build_data_source("github", _cfg())  # fallback = local data/data.json
    data = source.load()
    assert "projects" in data and len(data["projects"]) > 0
