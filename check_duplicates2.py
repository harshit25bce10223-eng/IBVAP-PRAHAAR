with open('tests/unit/test_detection_api.py', 'r') as f:
    lines = f.readlines()

for i, line in enumerate(lines[210:245], 211):
    if 'quality_state' in line or 'occlusion_state' in line:
        print(f'{i}: {repr(line)}')