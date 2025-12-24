import pytest
from project.downloader import ytdlp_client


class FakeYDL:
    def __init__(self, opts, info):
        self.opts = opts
        self._info = info

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download):
        return self._info

    def prepare_filename(self, info):
        return info.get("_prepared")


def _patch_yt_dlp(monkeypatch, info):
    monkeypatch.setattr(
        ytdlp_client.yt_dlp,
        "YoutubeDL",
        lambda opts: FakeYDL(opts, info),
    )


def test_download_uses_info_filepath(monkeypatch, tmp_path):
    f = tmp_path / "x.mp4"
    f.write_bytes(b"123")

    info = {"id": "id1", "filepath": str(f)}
    _patch_yt_dlp(monkeypatch, info)

    out = ytdlp_client.download("u", "best", str(tmp_path))

    assert out == str(f)


def test_download_uses_requested_downloads_filepath(monkeypatch, tmp_path):
    f = tmp_path / "x.mp4"
    f.write_bytes(b"123")

    info = {"id": "id1", "requested_downloads": [{"filepath": str(f)}]}
    _patch_yt_dlp(monkeypatch, info)

    out = ytdlp_client.download("u", "best", str(tmp_path))

    assert out == str(f)


def test_download_uses_prepare_filename(monkeypatch, tmp_path):
    f = tmp_path / "p.mp4"
    f.write_bytes(b"123")

    info = {"id": "id1", "_prepared": str(f)}
    _patch_yt_dlp(monkeypatch, info)

    out = ytdlp_client.download("u", "best", str(tmp_path))

    assert out == str(f)


def test_download_raises_when_missing(monkeypatch, tmp_path):
    info = {"id": "id1"}
    _patch_yt_dlp(monkeypatch, info)

    with pytest.raises(RuntimeError):
        ytdlp_client.download("u", "best", str(tmp_path))
