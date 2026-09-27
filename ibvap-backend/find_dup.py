with open('tests/unit/test_detection_api.py', 'rb') as f:
    content = f.read()

# Find the exact pattern
import re
for m in re.finditer(b'detection_state="DETECTED"', content):
    pos = m.start()
    line = content[:pos].count(b'\n') + 1
    context = content[max(0,m.start()-30):m.end()+50]
    print(f'Position {pos}, Line {line}: {context}')

print('---')
# Find the exact duplicate pattern
idx = content.find(b'detection_state="DETECTED",\n                quality_state="GOOD",\n                occlusion_state="LOW",\n                observed_at=datetime.now(timezone.utc),')
if idx >= 0:
    print('Found duplicate at byte:', idx)
else:
    print('Exact duplicate pattern not found')
    # Search for partial
    idx = content.find(b'detection_state="DETECTED",\n                quality_state="GOOD",')
    if idx >= 0:
        print('Found partial at:', idx)
        print(content[idx:idx+150].decode())