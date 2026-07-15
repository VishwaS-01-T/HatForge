import glob
import os

for file in glob.glob('c:/AudioPluginSamaan/hatforge/**/*.py', recursive=True):
    with open(file, 'rb') as f:
        raw = f.read()
    if raw.startswith(b'\xff\xfe'):
        text = raw.decode('utf-16le')
        print(f"Fixing {file}")
        with open(file, 'w', encoding='utf-8') as f:
            f.write(text)
    elif raw.startswith(b'\xfe\xff'):
        text = raw.decode('utf-16be')
        print(f"Fixing {file}")
        with open(file, 'w', encoding='utf-8') as f:
            f.write(text)
