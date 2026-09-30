import os

frontend_dir = r'c:\SIH\ibvap-frontend\src'
matches = []
for root, dirs, files in os.walk(frontend_dir):
    if 'tests' in root or '__tests__' in root:
        continue
    for f in files:
        if f.endswith(('.ts', '.tsx')):
            p = os.path.join(root, f)
            with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                for i, line in enumerate(fp):
                    if 'CAM-07' in line or 'CAM07' in line:
                        matches.append((p.replace(frontend_dir, ''), i+1, line.strip()))

for m in matches:
    safe_line = m[2].encode('ascii', 'ignore').decode('ascii')
    print(f'{m[0]}:{m[1]} -> {safe_line}')
