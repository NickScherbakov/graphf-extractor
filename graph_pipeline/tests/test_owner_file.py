def test_owner_file_content():
    with open("OWNER.md", encoding="utf-8") as f:
        content = f.read()
    assert "мейнтейнер" in content.lower()
    assert "@NickScherbakov" in content