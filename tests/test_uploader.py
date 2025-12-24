import pytest
from project.services import uploader


class FakeBot:
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []

    async def send_document(self, chat_id, document, caption=None):
        if self.fail:
            raise RuntimeError("Entity too large")
        self.sent.append((chat_id, str(document), caption))


class FakeTelethonClient:
    def __init__(self):
        self.disconnected = False
        self.sent_files = []

    async def send_file(self, entity, file, caption="", progress_callback=None):
        if progress_callback:
            progress_callback(50, 100)
            progress_callback(100, 100)
        self.sent_files.append((entity, file, caption))

    async def disconnect(self):
        self.disconnected = True


@pytest.mark.asyncio
async def test_send_file_smart_bot_api_success(tmp_path, monkeypatch):
    monkeypatch.setattr(uploader, "_telethon_client", None)

    bot = FakeBot()
    f = tmp_path / "a.txt"
    f.write_text("hi")

    pct = []
    await uploader.send_file_smart(bot, 1, f, on_progress=lambda p: pct.append(p))

    assert bot.sent
    assert pct == [100]


@pytest.mark.asyncio
async def test_send_file_smart_fallback_to_telethon(tmp_path, monkeypatch):
    bot = FakeBot(fail=True)
    fake_client = FakeTelethonClient()

    async def fake_get_client():
        return fake_client

    monkeypatch.setattr(uploader, "_get_telethon_client", fake_get_client)

    f = tmp_path / "big.bin"
    f.write_bytes(b"x")

    pct = []
    await uploader.send_file_smart(bot, 1, f, on_progress=lambda p: pct.append(p))

    assert fake_client.sent_files
    assert 100 in pct


@pytest.mark.asyncio
async def test_send_file_smart_raises_if_no_telethon(tmp_path, monkeypatch):
    bot = FakeBot(fail=True)

    async def fake_get_client():
        return None

    monkeypatch.setattr(uploader, "_get_telethon_client", fake_get_client)

    f = tmp_path / "x.bin"
    f.write_bytes(b"x")

    with pytest.raises(RuntimeError):
        await uploader.send_file_smart(bot, 1, f)


@pytest.mark.asyncio
async def test_close_telethon_client_disconnects(monkeypatch):
    fake_client = FakeTelethonClient()
    monkeypatch.setattr(uploader, "_telethon_client", fake_client)

    await uploader.close_telethon_client()

    assert fake_client.disconnected is True
    assert uploader._telethon_client is None
