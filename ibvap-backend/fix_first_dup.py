with open('tests/unit/test_detection_api.py', 'rb') as f:
    content = f.read()

old_text = b'''                confidence=0.9,
                quality_state="GOOD",
                occlusion_state="LOW",
                detection_state="DETECTED",
                quality_state="GOOD",
                occlusion_state="LOW",
                bbox_x=0.1, bbox_y=0.1, bbox_width=0.3, bbox_height=0.3,'''

new_text = b'''                confidence=0.9,
                quality_state="GOOD",
                occlusion_state="LOW",
                detection_state="DETECTED",
                bbox_x=0.1, bbox_y=0.1, bbox_width=0.3, bbox_height=0.3,'''

if old_text in content:
    content = content.replace(old_text, new_text)
    with open('tests/unit/test_detection_api.py', 'wb') as f:
        f.write(content)
    print("Fixed!")
else:
    print("Pattern not found")
    idx = content.find(b'confidence=0.9,\n                quality_state="GOOD",')
    if idx >= 0:
        print('Found at:', idx)
        print(content[idx:idx+300].decode())