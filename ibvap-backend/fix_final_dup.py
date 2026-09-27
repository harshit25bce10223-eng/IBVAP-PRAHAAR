with open('tests/unit/test_detection_api.py', 'rb') as f:
    content = f.read()

old_text = b'''                detection_state="DETECTED",
                quality_state="GOOD",
                occlusion_state="LOW",
                observed_at=datetime.now(timezone.utc),'''

new_text = b'''                detection_state="DETECTED",
                observed_at=datetime.now(timezone.utc),'''

if old_text in content:
    content = content.replace(old_text, new_text)
    with open('tests/unit/test_detection_api.py', 'wb') as f:
        f.write(content)
    print("Fixed!")
else:
    print("Pattern not found")
    idx = content.find(b'detection_state="DETECTED",\n                quality_state="GOOD",')
    if idx >= 0:
        print('Found at:', idx)
        print(content[idx:idx+200].decode())