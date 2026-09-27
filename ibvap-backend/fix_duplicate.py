with open('tests/unit/test_detection_api.py', 'r') as f:
    content = f.read()

# Replace the duplicate quality_state in the first detection
old_text = '''                confidence=0.9,
                quality_state="GOOD",
                occlusion_state="LOW",
                detection_state="DETECTED",
                quality_state="GOOD",
                occlusion_state="LOW",
                bbox_x=0.1, bbox_y=0.1, bbox_width=0.3, bbox_height=0.3,'''

new_text = '''                confidence=0.9,
                quality_state="GOOD",
                occlusion_state="LOW",
                detection_state="DETECTED",
                bbox_x=0.1, bbox_y=0.1, bbox_width=0.3, bbox_height=0.3,'''

if old_text in content:
    content = content.replace(old_text, new_text)
    with open('tests/unit/test_detection_api.py', 'w') as f:
        f.write(content)
    print("Fixed first detection")
else:
    print("Pattern not found for first detection")