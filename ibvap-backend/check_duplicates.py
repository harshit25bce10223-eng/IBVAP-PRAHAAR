with open('tests/unit/test_detection_api.py', 'rb') as f:
    content = f.read()

# Find all occurrences of the pattern
pattern = b'quality_state="GOOD", occlusion_state="LOW"'
count = content.count(pattern)
print(f'Count: {count}')

# Find all positions
pos = 0
while True:
    idx = content.find(b'quality_state="GOOD", occlusion_state="LOW"', pos)
    if idx == -1:
        break
    line_num = content[:idx].count(b'\n') + 1
    print(f'Found at byte {idx}, line {line_num}')
    pos = idx + 1