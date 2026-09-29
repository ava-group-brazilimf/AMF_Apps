import re
from pathlib import Path

schema_inv_path = Path('projects/Meu-ERP/outputs/asis/db/schema-inventory.md')
text = schema_inv_path.read_text(encoding='utf-8', errors='replace')
lines = text.splitlines()

RISK_ORDER = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
raw_table_rows = []
in_table_section = False
for i, line in enumerate(lines):
    if re.search(r'Table Inventory', line, re.I):
        in_table_section = True
        print(f'Table Inventory found at line {i}: {repr(line)}')
        continue
    if in_table_section:
        if re.match(r'^#{1,2}\s', line) and not re.match(r'^#{3,}', line):
            print(f'BREAK at line {i}: {repr(line)}')
            break
        if '|' not in line:
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 4:
            continue
        tname = parts[1].strip('`').strip()
        if not tname or tname.startswith('-') or tname.lower() == 'table':
            print(f'  Skip line {i} tname={repr(tname)}')
            continue
        print(f'  Would add: tname={repr(tname)}, len_parts={len(parts)}')
        raw_table_rows.append(tname)

print(f'\nFlat parser result: {len(raw_table_rows)} rows: {raw_table_rows[:10]}')

# Now try subsection parser
print('\n--- Testing subsection parser ---')
from build_summary_comprehensive import _parse_schema_subsections
er_col_counts = {}
risk_order = RISK_ORDER
result = _parse_schema_subsections(lines, er_col_counts, risk_order)
print(f'Subsection parser result: {len(result)} tables')
for r in result[:5]:
    print(f'  {r}')
