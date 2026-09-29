import re, json

html = open('projects/Meu-ERP/outputs/summary/AVA-FABRIC-SUMMARY-Meu-ERP-2026-05-24.html', encoding='utf-8', errors='replace').read()

# dbSchema
db_m = re.search(r'dbSchema\s*:\s*(\[.*?\]),', html, re.DOTALL)
if db_m:
    try:
        db = json.loads(db_m.group(1))
        first = db[0].get("t", db[0].get("tname", "?")) if db else "empty"
        print(f'dbSchema: {len(db)} tables — first: {first}')
    except Exception as e:
        print(f'dbSchema: parse error {e}')
else:
    print('dbSchema: NOT FOUND')

# gantt
gantt_m = re.search(r'"gantt"\s*:\s*"([^"]{0,200})', html)
if gantt_m:
    print(f'gantt: {repr(gantt_m.group(1)[:80])}')
else:
    print('gantt: NOT FOUND')

# waves
waves_m = re.search(r'waves\s*:\s*(\[.*?\])\s*,', html, re.DOTALL)
if waves_m:
    try:
        waves = json.loads(waves_m.group(1))
        print(f'waves: {len(waves)} entries — {[w["w"] for w in waves]}')
    except Exception as e:
        print(f'waves: parse error {e}')
else:
    print('waves: NOT FOUND or empty')

# effortRows
eff_m = re.search(r'D\.effortRows\s*=\s*(\[.*?\]);', html, re.DOTALL)
if eff_m:
    try:
        rows = json.loads(eff_m.group(1))
        print(f'effortRows: {len(rows)} rows — first: {rows[0]["module"] if rows else "empty"}')
    except Exception as e:
        print(f'effortRows: parse error {e}')
else:
    print('effortRows: not injected (empty)')

# infraRows
inf_m = re.search(r'D\.infraRows\s*=\s*(\[.*?\]);', html, re.DOTALL)
if inf_m:
    try:
        rows = json.loads(inf_m.group(1))
        print(f'infraRows: {len(rows)} rows — first: {rows[0]["resource"] if rows else "empty"}')
    except Exception as e:
        print(f'infraRows: parse error {e}')
else:
    print('infraRows: not injected (empty)')

# fileTypes — JS array with unquoted keys: [{t:".pas", q:"22",...}]
pas_m = re.search(r'\{t:"\.pas".*?q:"(\d+)"', html)
dfm_m = re.search(r'\{t:"\.dfm".*?q:"(\d+)"', html)
if pas_m or dfm_m:
    print(f'fileTypes .pas={pas_m.group(1) if pas_m else "?"}, .dfm={dfm_m.group(1) if dfm_m else "?"}')
