with open('tests/unit/test_detection_api.py', 'rb') as f:
    content = f.read()

# Find the exact bytes for the duplicate pattern
old_text = b'confidence=0.8,\n                quality_state="GOOD",\n                occlusion_state="LOW",\n                detection_state="DETECTED",\n                quality_state="GOOD",\n                occlusion_state="LOW",\n                observed_at=datetime.now(timezone.utc),'

new_text = b'confidence=0.8,\n                quality_state="GOOD",\n                occlusion_state="LOW",\n                detection_state="DETECTED",\n                observed_at=datetime.now(timezone.utc),'

if old_text in content:
    content = content.replace(old_text, new_text)
    with open('tests/unit/test_detection_api.py', 'wb') as f:
        f.write(content)
    print("Fixed second detection")
else:
    print("Pattern not found for second detection")
    # Debug: search for the pattern
    import re
    for m in re.finditer(b'confidence=0.8', content):
        pos = m.start()
        print(f'Found at byte {m.start()}: {content[m.start():m.start()+200]}')