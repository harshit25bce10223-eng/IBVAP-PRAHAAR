with open('tests/unit/test_detection_api.py', 'rb') as f:
    content = f.read()

idx = content.find(b'detection_state="DETECTED",\n                quality_state="GOOD",\n                occlusion_state="LOW",\n                observed_at=datetime.now(timezone.utc),')
print('Found at:', idx if idx >= 0 else 'NOT FOUND')
if idx >= 0:
    print(content[idx:idx+150].decode())