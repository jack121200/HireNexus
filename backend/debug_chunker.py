import re
from pathlib import Path

DATA_DIR = Path('data/raw')
filepath = str(DATA_DIR / '01_sde-general.txt')

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

raw_blocks = re.split(r'\n={3,}\n', content)
out = []
out.append(f'Total blocks: {len(raw_blocks)}')
for i, block in enumerate(raw_blocks[:6]):
    block = block.strip()
    out.append(f'\n--- Block {i} (len={len(block)}) ---')
    out.append(repr(block[:300]))
    lines = block.split('\n')
    is_header = all(
        line.startswith('TOPIC:') or line.startswith('ROLE:') or
        line.startswith('AUDIENCE:') or line.startswith('TAGS:') or line.strip() == ''
        for line in lines if line.strip()
    )
    has_topic = 'TOPIC:' in block
    has_role = 'ROLE:' in block
    out.append(f'  is_header={is_header}, has_TOPIC={has_topic}, has_ROLE={has_role}')
    out.append(f'  non-empty lines: {[l for l in lines if l.strip()][:5]}')

with open('debug_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print("Written to debug_output.txt")
