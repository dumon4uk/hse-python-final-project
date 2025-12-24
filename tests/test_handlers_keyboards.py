from project.handlers.download import kb_type, kb_formats


def test_kb_type_buttons():
    kb = kb_type()
    texts = [b.text for row in kb.inline_keyboard for b in row]
    cbs = [b.callback_data for row in kb.inline_keyboard for b in row]

    assert "🎬 Видео" in texts
    assert "dl:type:video" in cbs
    assert "dl:cancel" in cbs


def test_kb_formats_buttons():
    kb = kb_formats([{"id": "1", "label": "x"}])
    cbs = [b.callback_data for row in kb.inline_keyboard for b in row]

    assert "dl:fmt:1" in cbs
    assert "dl:back:type" in cbs
    assert "dl:cancel" in cbs
