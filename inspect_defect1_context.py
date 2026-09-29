#!/usr/bin/env python3
from pathlib import Path

p = Path(r"c:\_git\Fix\imfai-ava-fabric-apps-agents\projects\MeuERP-001\outputs\summary\AVA-FABRIC-SUMMARY-MeuERP-001-2026-08-04.html")
text = p.read_text(encoding="utf-8", errors="ignore")

off = 16213238
start = text.rfind('<pre', 0, off)
print('pre start', start)
print('TAG:', text[start:start+120])
print('---')
print('BEFORE (300 chars):')
print(text[start-300:start])
print('---')
print('AFTER (300 chars):')
end = text.find('</pre>', start) + 6
print(text[start:end])
