with open('tests/unit/test_detection_api.py', 'r') as f:
    content = f.read()

# Replace the duplicate quality_state in the second detection
old_text = '''                confidence=0.8,
                quality_state="GOOD",
                occlusion_state="LOW",
                detection_state="DETECTED",
                quality_state="GOOD",
                occlusion_state="LOW",
                observed_at=datetime.now(timezone.utc),'''

new_text = '''                confidence=0.8,
                quality_state="GOOD",
                occlusion_state="LOW",
                detection_state="DETECTED",
                observed_at=datetime.now(timezone.utc),'''

if old_text in content:
    content = content.replace(old_text, new_text)
    with open('tests/unit/test_detection_api.py', 'w') as f:
        f.write(content)
    print("Fixed second detection")
else:
    print("Pattern not found for second detection")