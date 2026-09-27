with open('tests/unit/test_detection_api.py', 'rb') as f:
    content = f.read()

old_text = b'''                confidence=0.8,
                quality_state="GOOD",
                occlusion_state="LOW",
                detection_state="DETECTED",
                quality_state="GOOD",
                occlusion_state="LOW",
                observed_at=datetime.now(timezone.utc),'''

new_text = b'''                confidence=0.8,
                quality_state="GOOD",
                occlusion_state="LOW",
                detection_state="DETECTED",
                observed_at=datetime.now(timezone.utc),'''

if old_text in content:
    content = content.replace(old_text, new_text)
    with open('tests/unit/test_detection_api.py', 'wb') as f:
        f.write(content)
    print("Fixed!")
else:
    print("Pattern not found")
    # Debug: search for the pattern
    idx = content.find(b'confidence=0.8')
    if idx >= 0:
        print('Found at:', content[idx:idx+200])