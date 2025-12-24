from project.services.download import make_job_dir, DownloadRequest, download_and_prepare_sync, cleanup_dir


def test_make_job_dir_with_chat_id(tmp_path):
    base = str(tmp_path)
    p = make_job_dir(base, chat_id=123)
    assert "/123/" in p.replace("\\", "/")


def test_cleanup_dir_removes(tmp_path):
    d = tmp_path / "job"
    d.mkdir()
    (d / "a.txt").write_text("x")

    cleanup_dir(str(d))

    assert not d.exists()


def test_download_and_prepare_sync_calls_ytdlp(monkeypatch, tmp_path):
    called = {}

    def fake_ytdlp_download(url, format_id, out_dir, progress_hook=None, to_mp3=False, cookies_file=None):
        called["url"] = url
        called["format_id"] = format_id
        called["to_mp3"] = to_mp3
        return str(tmp_path / "file.mp4")

    monkeypatch.setattr("project.services.download.ytdlp_download", fake_ytdlp_download)

    req = DownloadRequest(url="http://x", format_id="best", to_mp3=True)
    out = download_and_prepare_sync(req, str(tmp_path))

    assert out.endswith("file.mp4")
    assert called["format_id"] == "best"
    assert called["to_mp3"] is True
