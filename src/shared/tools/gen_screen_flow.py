#!/usr/bin/env python3
import argparse, json, re, subprocess, sys
from collections import defaultdict
from pathlib import Path

MERMAID_MAX_CHARS = 40000   # conservative limit; default renderer cap is ~50k
ITEMS_PER_SPLIT   = 120     # max nodes per detail diagram before splitting
RECURSIVE_SUBGROUP_THRESHOLD = 40   # trigger recursive sub-diagrams when a group exceeds this
MAX_RECURSIVE_LEVELS = 3            # overview (0) -> BC (1) -> subgroup (2) -> leaf (3)

def parse_bc_map(bc_map_path):
    bcs = {}
    try:
        content = bc_map_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return {}

    # Accept both H2 (## BC-NN: Nome) and H3 (### BC-XX: Name) sections.
    # The section header itself becomes the first line of each chunk.
    for section in re.split(r'\n(?:##|###)\s+', '\n' + content)[1:]:
        lines = section.split('\n')
        m = re.match(r'(BC-\d+)[\s:\u2014\-]+(.+)', lines[0].strip())
        if not m:
            continue
        bc_id, bc_name = m.group(1).strip(), m.group(2).strip()
        bc_label = f'{bc_id}: {bc_name}'
        units = []
        for line in lines[1:]:
            # Delphi format: **Units list**: u1.pas, u2.pas
            # .NET format:  **Files**: file1.cs, file2.vb
            u = re.match(
                r'\*\*(?:Units list|Files)[\*\s]*(?:\(.*?\))?\s*:\s*(.+)',
                line.strip(),
            )
            if u:
                units = [
                    Path(x.strip()).stem.lower()
                    for x in u.group(1).split(',')
                    if x.strip()
                ]
        bcs[bc_label] = {'name': bc_name, 'units': units, 'tokens': set(tokenize(bc_name))}

    # Fallback: markdown table (e.g. | BC-01 | Estoque | `SysEstq` | 38 | 36 |)
    if not bcs:
        for line in content.splitlines():
            if '|' not in line or 'BC-' not in line or '---' in line or 'Código' in line:
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 5:
                bc_id = parts[1]
                bc_name = parts[2]
                src_dirs = parts[3].replace('`', '').split()
                if re.match(r'BC-\d+', bc_id) and bc_name:
                    bc_label = f'{bc_id}: {bc_name}'
                    units = [d.lower() for d in src_dirs]
                    bcs[bc_label] = {'name': bc_name, 'units': units}
    return bcs

NOISE = {
    # Delphi/VCL
    'frm','dfm','pas','web','form','data','unit','main','base','lib','utils','test',
    # .NET / ASP.NET / VB6 / WPF
    'cs','vb','aspx','cshtml','vbhtml','ascx','svc','asmx','resx','designer','xaml','xml','config',
    'controller','view','model','page','webpage','window','dialog','usercontrol','master','masterpage',
    'partial','shared','component','handler','module','service',
}

def tokenize(text):
    """Split text into domain tokens, handling PascalCase, snake_case and kebab-case."""
    parts = re.split(r'[^A-Za-z0-9]+', str(text))
    tokens = []
    for p in parts:
        # Split PascalCase / camelCase while preserving contiguous ALL-CAPS abbreviations.
        tokens.extend(re.findall(r'[a-z]+|[A-Z][a-z]*|[A-Z]+(?=[A-Z][a-z]|\b)', p))
    return [t.lower() for t in tokens if len(t) >= 3]

def build_token_index(bcs):
    exact, tcounts = {}, defaultdict(lambda: defaultdict(int))
    for bc_label, info in bcs.items():
        for unit in info['units']:
            exact[unit] = bc_label
            for tok in tokenize(unit):
                if tok not in NOISE:
                    tcounts[tok][bc_label] += 1
    token_to_bc = {tok: max(bc_counts, key=bc_counts.get) for tok, bc_counts in tcounts.items()}
    token_pairs = sorted(token_to_bc.items(), key=lambda x: -len(x[0]))
    return exact, token_pairs

def classify_form(form, exact, token_pairs, nav_domains=None, bc_labels=None):
    sf = form.get('source_file', '')
    fn = form.get('form_name', '')
    src_stem = Path(sf.replace('\\', '/')).stem.lower() if sf else ''
    if src_stem and src_stem in exact:
        return exact[src_stem]
    combined = (fn + ' ' + sf).lower()
    for tok, bc in token_pairs:
        if tok in combined:
            return bc
    # Fallback: screen-navigation-map.md domain classification
    if nav_domains and src_stem:
        for domain, stems in nav_domains.items():
            if src_stem in stems:
                # Normalize nav-map domain to existing BC label if possible
                if bc_labels:
                    bc_norm = {re.sub(r'[^a-z]', '', re.sub(r'^BC-\d+:\s*', '', b).lower()): b for b in bc_labels}
                    domain_key = re.sub(r'[^a-z]', '', domain.lower())
                    if domain_key in bc_norm:
                        return bc_norm[domain_key]
                return domain
    if sf:
        parts = sf.replace('\\\\', '/').split('/')
        for p in reversed(parts[:-1]):
            if p.strip():
                return p.strip()
    return 'Unclassified'

def _get_str(record, *keys):
    for k in keys:
        if isinstance(record, dict) and k in record:
            v = record[k]
            return str(v) if v is not None else ''
    return ''


def _get_list(record, key):
    if not isinstance(record, dict):
        return []
    v = record.get(key)
    return v if isinstance(v, list) else []


def _get_nested(record, *keys):
    """Safely traverse nested dicts; returns '' if any step is missing/invalid."""
    cur = record
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return ''
        cur = cur[k]
    return str(cur) if cur is not None else ''


def extract_forms(raw_data):
    """Return the raw form/page list from either Delphi or .NET analyzer JSON."""
    if not isinstance(raw_data, dict):
        return []
    # Delphi analyzer schema: { payload: { forms: [...] } }
    payload_lower = raw_data.get('payload')
    if isinstance(payload_lower, dict) and isinstance(payload_lower.get('forms'), list):
        return payload_lower['forms']
    # .NET analyzer schema: { Payload: [...] }
    payload_upper = raw_data.get('Payload')
    if isinstance(payload_upper, list):
        return payload_upper
    # Defensive: some .NET artifacts may wrap forms in a dict as well.
    if isinstance(payload_upper, dict) and isinstance(payload_upper.get('forms'), list):
        return payload_upper['forms']
    return []


def normalize_form(record):
    """Normalize a Delphi or .NET form record to the internal schema."""
    if not isinstance(record, dict):
        return {
            'form_name': str(record) if record is not None else '',
            'source_file': '',
            'field_count': 0,
            'form_type': '',
        }

    # form_name / Name
    form_name = (
        _get_str(record, 'form_name')
        or _get_str(record, 'Name')
        or _get_str(record, 'name')
    )

    # source_file / SourceRef.file
    source_file = (
        _get_str(record, 'source_file')
        or _get_nested(record, 'SourceRef', 'file')
        or _get_nested(record, 'source_ref', 'file')
        or _get_str(record, 'file')
        or _get_str(record, 'SourceFile')
    )

    # field_count / len(Controls)
    field_count = 0
    if 'field_count' in record and record['field_count'] is not None:
        try:
            field_count = int(record['field_count'])
        except (TypeError, ValueError):
            field_count = 0
    else:
        controls = _get_list(record, 'Controls') or _get_list(record, 'controls') or _get_list(record, 'fields')
        field_count = len(controls)

    form_type = (
        _get_str(record, 'form_type')
        or _get_str(record, 'FormType')
        or _get_str(record, 'type')
    )

    return {
        'form_name': form_name,
        'source_file': source_file,
        'field_count': field_count,
        'form_type': form_type,
    }


def sid(name):
    return 'N_' + re.sub(r'[^A-Za-z0-9]', '_', name)[:55]

def slabel(name):
    return name.replace('"', "'").replace('<', '').replace('>', '')

def validate_and_write(content, path, validator):
    result = subprocess.run(
        [sys.executable, str(validator), '--output', str(path)],
        input=content, capture_output=True, text=True)
    return result.returncode

def generate_overview(bc_groups, total_forms):
    lines = ['flowchart TD',
             f'    %% Screen Flow Overview  — {total_forms} forms across {len(bc_groups)} groups',
             '    MAIN["Entry Point / MDI Host"]', '']
    for g in sorted(bc_groups.keys()):
        gid = sid(g)
        cnt = len(bc_groups[g])
        lines.append(f'    {gid}["{slabel(g)}\\n({cnt} forms)"]')
        lines.append(f'    MAIN --> {gid}')
    lines.append('')
    return '\n'.join(lines) + '\n'

def generate_bc_detail(bc_label, forms, part=None, total_parts=None):
    title = slabel(bc_label)
    if part and total_parts and total_parts > 1:
        title += f' — Part {part}/{total_parts}'
    lines = ['flowchart TD',
             f'    %% {title} — {len(forms)} forms',
             f'    BC["{slabel(title)}"]', '']
    for f in sorted(forms, key=lambda x: x.get('form_name', '')):
        fn = f.get('form_name', '')
        nid = sid(fn)
        lbl = slabel(fn)
        fc = f.get('field_count', 0)
        if fc:
            lbl += f' [{fc}f]'
        lines.append(f'    {nid}["{lbl}"]')
        lines.append(f'    BC --> {nid}')
    return '\n'.join(lines) + '\n'

def partition_forms_by_directory(forms):
    """Group forms by the immediate parent directory of source_file."""
    groups = defaultdict(list)
    for f in forms:
        sf = f.get('source_file', '')
        if sf:
            p = Path(sf.replace('\\', '/'))
            key = p.parent.name.strip() if p.parent.name.strip() else 'root'
        else:
            key = 'no-source'
        groups[key].append(f)
    return dict(groups)


def partition_forms_by_prefix(forms, prefix_len=4):
    """Group forms by the first prefix_len characters of form_name."""
    groups = defaultdict(list)
    for f in forms:
        fn = f.get('form_name', '')
        key = (fn[:prefix_len].lower() if len(fn) >= prefix_len else fn.lower()) or 'other'
        groups[key].append(f)
    return dict(groups)


def choose_prefix_partition(forms, threshold):
    """Find a prefix length that keeps every subgroup <= threshold."""
    for prefix_len in range(3, 25):
        groups = partition_forms_by_prefix(forms, prefix_len)
        if groups and max(len(g) for g in groups.values()) <= threshold:
            return groups
    return None


def slugify(text):
    return re.sub(r'[^A-Za-z0-9]', '-', str(text))[:40].strip('-')


def generate_recursive_details(forms, label, slug, level, stem, out_dir, validator, generated, threshold=RECURSIVE_SUBGROUP_THRESHOLD, max_levels=MAX_RECURSIVE_LEVELS, max_forms=0):
    """Recursively generate lower-level screen-flow diagrams for large groups.

    Level 0 = overview (handled by caller), level 1 = BC, level 2+ = subgroups.
    """
    effective_threshold = min(threshold, max_forms) if max_forms > 0 else threshold
    can_split = len(forms) > effective_threshold and level < max_levels

    if not can_split:
        # If an explicit max-forms cap remains exceeded, chunk alphabetically.
        chunk_size = max_forms if max_forms > 0 and len(forms) > max_forms else effective_threshold
        if max_forms > 0 and len(forms) > max_forms:
            chunks = list(chunk(forms, max_forms))
        else:
            chunks = [forms]
        total = len(chunks)
        for idx, ch in enumerate(chunks):
            fname = f'{stem}-{slug}.mmd' if total == 1 else f'{stem}-{slug}-p{idx+1}.mmd'
            fpath = out_dir / fname
            detail = generate_bc_detail(label, ch, part=(idx+1) if total > 1 else None, total_parts=total if total > 1 else None)
            rc = validate_and_write(detail, fpath, validator)
            generated.append((fname, len(detail), rc))
        return

    # First try directory-based grouping; fall back to prefix-based.
    subgroups = partition_forms_by_directory(forms)
    if not subgroups or len(subgroups) == 1 or max(len(g) for g in subgroups.values()) > effective_threshold:
        prefix_groups = choose_prefix_partition(forms, effective_threshold)
        if prefix_groups:
            subgroups = prefix_groups

    for sub_label, sub_forms in sorted(subgroups.items()):
        sub_slug = f'{slug}-{slugify(sub_label)}'
        sub_title = f'{label} / {sub_label}'
        generate_recursive_details(
            sub_forms, sub_title, sub_slug, level + 1, stem, out_dir, validator,
            generated, threshold, max_levels, max_forms,
        )


def write_manifest(out_dir, stem, total_forms, generated):
    """Write a JSON manifest listing all generated diagram files."""
    manifest = {
        'artifact': stem,
        'total_forms': total_forms,
        'generated_files': [
            {'file': name, 'size': size, 'status': 'PASS' if rc in (0, 2) else 'FAIL'}
            for name, size, rc in generated
        ],
        'pass_count': sum(1 for _, _, rc in generated if rc in (0, 2)),
        'fail_count': sum(1 for _, _, rc in generated if rc not in (0, 2)),
    }
    path = out_dir / f'{stem}-manifest.json'
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')


def parse_nav_map(nav_map_path):
    """Parse screen-navigation-map.md to build a secondary form→domain mapping.
    Returns dict: domain_name → set of lower-case file stems."""
    domains = {}
    if not nav_map_path or not nav_map_path.exists():
        return domains
    content = nav_map_path.read_text(encoding='utf-8')
    current_domain = None
    for line in content.splitlines():
        m = re.match(r'###\s+(.+?)\s*\(', line.strip())
        if m:
            current_domain = m.group(1).strip()
            domains[current_domain] = set()
            continue
        if current_domain and '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4 and not parts[0].startswith('---') and not parts[0].startswith('Form'):
                file_name = parts[2]  # Arquivo column (dfm file)
                stem = Path(file_name).stem.lower()
                if stem:
                    domains[current_domain].add(stem)
    return domains

def chunk(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i+size]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--bc-map')
    parser.add_argument('--nav-map')
    parser.add_argument('--max-forms', type=int, default=0,
                        help='Max forms per diagram before auto-splitting (0=disable)')
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.output)
    bc_map_path = Path(args.bc_map) if args.bc_map else Path(
        f'projects/{args.project}/outputs/asis/bounded-context-map.md')

    if not input_path.exists():
        print(f'ERROR: Input not found: {input_path}', file=sys.stderr); sys.exit(1)

    bcs = parse_bc_map(bc_map_path)
    exact, token_pairs = build_token_index(bcs)
    total_units = sum(len(i['units']) for i in bcs.values())
    print(f'[gen_screen_flow] BC map: {len(bcs)} BCs, {total_units} units, {len(token_pairs)} tokens')

    nav_map_path = Path(args.nav_map) if args.nav_map else Path(
        f'projects/{args.project}/outputs/asis/docs/screen-navigation-map.md')
    nav_domains = parse_nav_map(nav_map_path)
    if nav_domains:
        print(f'[gen_screen_flow] Navigation map: {len(nav_domains)} domains loaded')

    with open(input_path, encoding='utf-8') as fh:
        raw_data = json.load(fh)
    raw_forms = extract_forms(raw_data)
    forms = [normalize_form(r) for r in raw_forms]
    if not forms:
        print('ERROR: No forms', file=sys.stderr); sys.exit(1)

    bc_groups = defaultdict(list)
    bc_labels = list(bcs.keys())
    for f in forms:
        bc_groups[classify_form(f, exact, token_pairs, nav_domains, bc_labels)].append(f)
    classified = sum(len(v) for g, v in bc_groups.items() if g != 'Unclassified')
    print(f'[gen_screen_flow] {len(forms)} forms, {len(bc_groups)} groups, {classified} classified')

    output_path.parent.mkdir(parents=True, exist_ok=True)
    validator = Path('src/shared/utils/validate_diagram.py')
    generated = []

    # 1. Overview file (the --output path)
    overview = generate_overview(bc_groups, len(forms))
    rc = validate_and_write(overview, output_path, validator)
    generated.append((output_path.name, len(overview), rc))

    # 2. Per-BC detail files (recursive lower-level diagrams for large BCs)
    stem = output_path.stem  # 'screen-flow'
    out_dir = output_path.parent
    for bc_label in sorted(bc_groups.keys()):
        items = bc_groups[bc_label]
        bc_slug = slugify(bc_label)
        generate_recursive_details(
            items, bc_label, bc_slug, level=1, stem=stem, out_dir=out_dir,
            validator=validator, generated=generated,
            threshold=RECURSIVE_SUBGROUP_THRESHOLD,
            max_levels=MAX_RECURSIVE_LEVELS,
            max_forms=args.max_forms,
        )

    # 3. Manifest with generated files
    write_manifest(out_dir, stem, len(forms), generated)

    print(f'[gen_screen_flow] Generated {len(generated)} files:')
    for name, size, rc in generated:
        status = 'PASS' if rc in (0, 2) else 'FAIL'
        print(f'  [{status}] {name} ({size} chars)')
    sys.exit(0 if all(r in (0, 2) for _, _, r in generated) else 1)

if __name__ == '__main__':
    main()
