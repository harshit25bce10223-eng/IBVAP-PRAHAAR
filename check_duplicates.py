with open('tests/unit/test_detection_api.py', 'rb') as f:
    content = f.read()

# Find all occurrences of the pattern
patterns = [
    b'quality_state="GOOD", occlusion_state="LOW"',
    b'quality_state="GOOD",',
    b'occlusion_state="LOW"',
]

for pattern in [b'quality_state="GOOD", occlusion_state="LOW"', b'quality_state="GOOD",', b'occlusion_state="LOW"']:
    count = content.count(pattern)
    print(f'Pattern {pattern}: Count = {count}')

# Find all positions for the problematic pattern
pattern = b'quality_state="GOOD", occlusion_state="LOW"'
pos = 0
while True:
    idx = content.find(pattern, pos)
    if idx == -1:
        break
    line_num = content[:idx].count(b'\n') + 1
    print(f'Found at byte {idx}, line {line_num}')
    pos = idx + 1