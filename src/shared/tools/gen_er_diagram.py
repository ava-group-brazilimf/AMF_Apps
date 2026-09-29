#!/usr/bin/env python3
"""Gera diagramas ER no formato erDiagram do Mermaid a partir de schemas de banco."""
import argparse, json, re, subprocess, sys
from collections import defaultdict
from pathlib import Path

ITEMS_PER_SPLIT = 50
RECURSIVE_SUBGROUP_THRESHOLD = 25   # trigger recursive sub-diagrams when a group exceeds this
MAX_RECURSIVE_LEVELS = 3            # overview (0) -> BC (1) -> subgroup (2) -> leaf (3)

TYPE_MAP = {
    'valors': 'int', 'valori': 'int', 'valorn': 'int', 'valorps': 'int',
    'valor_monetario': 'decimal', 'valor_monetario_def': 'decimal',
    'numero_grande_4cd': 'int', 'numero_grande_2cd': 'int',
    'numero_grande_6cd': 'int', 'numero_grande_def': 'int',
    'descricao_50rq': 'string', 'descricao_20rq': 'string',
    'descricao_15': 'string', 'descricao_30': 'string',
    'descricao_200': 'string', 'descricao_100': 'string',
    'descricao_500': 'string', 'descricao_1000': 'text',
    'descricao': 'string', 'descricao_grande': 'text',
    'nome': 'string', 'nome_50rq': 'string',
    'nome_operador_def': 'string', 'nome_operador': 'string',
    'nome_completo': 'string', 'nome_fantasia': 'string',
    'data_hora_def': 'datetime', 'data_hora': 'datetime',
    'data': 'date', 'hora': 'time', 'data_nascimento': 'date',
    'sim_nao': 'boolean', 'flag': 'boolean',
    'cpf_cnpj': 'string', 'cnpj': 'string', 'cpf': 'string',
    'email': 'string', 'telefone': 'string', 'celular': 'string',
    'cep': 'string', 'endereco': 'string',
    'observacao': 'text', 'quantidade': 'int', 'qtd': 'int', 'quant': 'int',
    'percentual': 'int', 'perc': 'int',
    'codigo': 'string', 'cod': 'string', 'sigla': 'string',
    'status': 'string', 'situacao': 'string',
    'tipo': 'string', 'seq': 'int', 'sequencia': 'int',
    'numero': 'int', 'num': 'int',
    'ano': 'int', 'mes': 'int', 'dia': 'int',
    'id': 'int', 'uuid': 'string', 'guid': 'string',
    'url': 'string', 'path': 'string', 'arquivo': 'string',
    'blob': 'blob', 'imagem': 'blob', 'documento': 'blob',
    'json': 'json', 'xml': 'xml', 'texto': 'text',
    'chave': 'string', 'token': 'string', 'senha': 'string',
}


def map_type(raw):
    t = raw.lower().strip().replace(' ', '_')
    r = TYPE_MAP.get(t)
    if r:
        return r
    if 'data' in t and 'hora' not in t:
        return 'date'
    if 'hora' in t:
        return 'time'
    if 'valor' in t or 'vlr' in t or t.startswith('v_'):
        return 'decimal'
    if 'desc' in t or 'nome' in t or 'texto' in t or 'dsc_' in t:
        return 'string'
    if any(x in t for x in ['num', 'qtd', 'qtde', 'quant', 'seq', 'cod']):
        return 'int'
    if any(x in t for x in ['flag', 'ativo', 'bloqueado', 'cancelado', 'situacao', 'status', 'sim']):
        return 'boolean'
    return 'string'


def sid(name):
    return re.sub(r'[^A-Za-z0-9_]', '_', name)[:55]


def slabel(name):
    return name.replace('"', "'")


def parse_bc_map(bc_map_path):
    bcs = {}
    try:
        content = bc_map_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return {}
    for section in re.split(r'\n## ', '\n' + content)[1:]:
        lines = section.split('\n')
        m = re.match(r'(BC-\d+)[\s:\u2014\-]+(.+)', lines[0].strip())
        if not m:
            continue
        bc_id, bc_name = m.group(1).strip(), m.group(2).strip()
        bc_label = f'{bc_id}: {bc_name}'
        key_tables = []
        for line in lines[1:]:
            tm = re.match(r'\*\*(?:Key tables|DB Tables \(key\))[:\*]*\*?\s*(.+)', line.strip())
            if tm:
                for tick, plain in re.findall(r' ([^ ]+) |([A-Za-z_][A-Za-z0-9_]*)', tm.group(1)):
                    n = (tick or plain).strip().lower()
                    if n:
                        key_tables.append(n)
        bcs[bc_label] = {'name': bc_name, 'key_tables': key_tables}
    return bcs


NOISE = {'tmp', 'log', 'aux', 'old', 'new', 'bak', 'cfg', 'all', 'tab'}


def tokenize(text):
    return [p.lower() for p in re.findall(r'[a-z]+|[A-Z][a-z]*', text) if len(p) >= 3]


def build_table_index(bcs):
    exact, prefix_list, tcounts = {}, [], defaultdict(lambda: defaultdict(int))
    for bc_label, info in bcs.items():
        for tbl in info['key_tables']:
            tl = tbl.lower()
            exact[tl] = bc_label
            prefix_list.append((tl, bc_label))
            for tok in tokenize(tl):
                if tok not in NOISE:
                    tcounts[tok][bc_label] += 1
    prefix_list.sort(key=lambda x: -len(x[0]))
    token_to_bc = {tok: max(bc_counts, key=bc_counts.get) for tok, bc_counts in tcounts.items()}
    token_pairs = sorted(token_to_bc.items(), key=lambda x: -len(x[0]))
    return exact, prefix_list, token_pairs


def compute_prefix_groups(tables, min_count=3, prefix_len=4):
    counts = defaultdict(int)
    for t in tables:
        n = t.get('name', '')
        if len(n) >= prefix_len:
            counts[n[:prefix_len].lower()] += 1
    common = {p for p, c in counts.items() if c >= min_count}
    return {t.get('name', '').lower(): (f"Prefix: {t.get('name', '')[:prefix_len].lower()}" if t.get('name', '')[:prefix_len].lower() in common else 'Other') for t in tables}


def classify_table(name, exact, prefix_list, token_pairs, prefix_groups):
    nl = name.lower()
    if nl in exact:
        return exact[nl]
    for pfx, bc in prefix_list:
        if nl.startswith(pfx) or pfx.startswith(nl) and len(nl) >= 4:
            return bc
    for tok, bc in token_pairs:
        if tok in nl:
            return bc
    return prefix_groups.get(nl, 'Other')


def validate_and_write(content, path, validator):
    result = subprocess.run(
        [sys.executable, str(validator), '--output', str(path)],
        input=content, capture_output=True, text=True)
    return result.returncode


def generate_overview(domain_groups, total_tables):
    lines = ['erDiagram',
             f'    %% ER Diagram Overview - {total_tables} tables across {len(domain_groups)} groups', '']
    for g in sorted(domain_groups.keys()):
        gid = sid(g)
        cnt = len(domain_groups[g])
        lines.append(f'    {gid} {{')
        lines.append(f'        string group_name "{slabel(g)}"')
        lines.append(f'        int table_count "{cnt}"')
        lines.append('    }')
    lines.append('')
    for g in sorted(domain_groups.keys()):
        gid = sid(g)
        for t in domain_groups[g]:
            tname = t.get('name', '')
            if tname:
                lines.append(f'    {sid(tname)} ||--|| {gid} : belongs_to')
    lines.append('')
    return '\n'.join(lines) + '\n'


def generate_bc_detail(bc_label, tables, part=None, total_parts=None):
    title = slabel(bc_label)
    if part and total_parts and total_parts > 1:
        title += f' Part {part}/{total_parts}'
    lines = ['erDiagram',
             f'    %% {title} - {len(tables)} tables', '']
    for t in sorted(tables, key=lambda x: x.get('name', '')):
        name = t.get('name', '')
        if not name:
            continue
        nid = sid(name)
        lines.append(f'    {nid} {{')
        cols = t.get('columns', [])
        if cols:
            for c in cols:
                cn = c.get('name', '')
                ct = map_type(c.get('data_type', 'string'))
                lines.append(f'        {ct} {cn}')
        else:
            # Mermaid requires at least one attribute per entity
            lines.append(f'        string placeholder')
        lines.append('    }')
    fks = set()
    for t in sorted(tables, key=lambda x: x.get('name', '')):
        tname = sid(t.get('name', ''))
        pk_cols = set(t.get('primary_key', []))
        for c in t.get('columns', []):
            cn = c.get('name', '')
            cn_upper = cn.upper()
            is_fk = c.get('fk') == True
            if not is_fk:
                is_fk = (cn_upper.startswith('FK_') or
                        cn_upper.startswith('REF_') or
                        (cn_upper.startswith('ID_') and cn not in pk_cols))
            if is_fk:
                target = ''
                if cn_upper.startswith('FK_'):
                    target = sid(cn_upper[3:])
                elif cn_upper.startswith('REF_'):
                    target = sid(cn_upper[4:])
                elif cn_upper.startswith('ID_') and cn_upper[3:] != t.get('name', '').upper():
                    target = sid(cn_upper[3:])
                for fk_entry in t.get('foreign_keys', []):
                    if isinstance(fk_entry, dict):
                        ref_table = fk_entry.get('table', fk_entry.get('references', ''))
                        if ref_table:
                            target = sid(ref_table)
                    elif isinstance(fk_entry, str):
                        target = sid(fk_entry) if fk_entry else target
                if target and target != tname:
                    rel = f'    {target} ||--o{{ {tname} : "fk_{slabel(cn)}"'
                    fks.add(rel)
        for fk_entry in t.get('foreign_keys', []):
            target = ''
            tgt_col = ''
            if isinstance(fk_entry, dict):
                target = sid(fk_entry.get('table', fk_entry.get('references', '')))
                tgt_col = fk_entry.get('column', '')
            elif isinstance(fk_entry, str):
                parts = fk_entry.split('.')
                if len(parts) == 2:
                    target, tgt_col = sid(parts[0]), parts[1]
                elif len(parts) == 1:
                    target = sid(parts[0])
            if target and target != tname:
                lbl = f'fk_{slabel(tgt_col)}' if tgt_col else 'fk'
                rel = f'    {target} ||--o{{ {tname} : "{lbl}"'
                fks.add(rel)
    lines.extend(sorted(fks))
    lines.append('')
    return '\n'.join(lines) + '\n'


def chunk(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i+size]


def slugify(text):
    return re.sub(r'[^A-Za-z0-9]', '-', str(text))[:40].strip('-')


def partition_tables_by_prefix(tables, prefix_len=4):
    """Group tables by the first prefix_len characters of the table name."""
    groups = defaultdict(list)
    for t in tables:
        name = t.get('name', '')
        key = (name[:prefix_len].lower() if len(name) >= prefix_len else name.lower()) or 'other'
        groups[key].append(t)
    return dict(groups)


def choose_prefix_partition(tables, threshold):
    """Find a prefix length that keeps every subgroup <= threshold."""
    for prefix_len in range(3, 25):
        groups = partition_tables_by_prefix(tables, prefix_len)
        if groups and max(len(g) for g in groups.values()) <= threshold:
            return groups
    return None


def generate_recursive_details(tables, label, slug, level, stem, out_dir, validator, generated, threshold=RECURSIVE_SUBGROUP_THRESHOLD, max_levels=MAX_RECURSIVE_LEVELS, max_tables=0):
    """Recursively generate lower-level ER diagrams for large groups.

    Level 0 = overview (handled by caller), level 1 = BC/domain, level 2+ = subgroups.
    """
    effective_threshold = min(threshold, max_tables) if max_tables > 0 else threshold
    can_split = len(tables) > effective_threshold and level < max_levels

    if not can_split:
        # If an explicit max-tables cap remains exceeded, chunk alphabetically.
        if max_tables > 0 and len(tables) > max_tables:
            chunks = list(chunk(tables, max_tables))
        else:
            chunks = [tables]
        total = len(chunks)
        for idx, ch in enumerate(chunks):
            fname = f'{stem}-{slug}.mmd' if total == 1 else f'{stem}-{slug}-p{idx+1}.mmd'
            fpath = out_dir / fname
            detail = generate_bc_detail(label, ch, part=(idx+1) if total > 1 else None, total_parts=total if total > 1 else None)
            rc = validate_and_write(detail, fpath, validator)
            generated.append((fname, len(detail), rc))
        return

    subgroups = choose_prefix_partition(tables, effective_threshold)
    if not subgroups:
        # Fallback: alphabetical half-split
        mid = len(tables) // 2
        subgroups = {
            'a-m': tables[:mid],
            'n-z': tables[mid:],
        }

    for sub_label, sub_tables in sorted(subgroups.items()):
        sub_slug = f'{slug}-{slugify(sub_label)}'
        sub_title = f'{label} / {sub_label}'
        generate_recursive_details(
            sub_tables, sub_title, sub_slug, level + 1, stem, out_dir, validator,
            generated, threshold, max_levels, max_tables,
        )


def write_manifest(out_dir, stem, total_tables, generated):
    """Write a JSON manifest listing all generated ER diagram files."""
    manifest = {
        'artifact': stem,
        'total_tables': total_tables,
        'generated_files': [
            {'file': name, 'size': size, 'status': 'PASS' if rc in (0, 2) else 'FAIL'}
            for name, size, rc in generated
        ],
        'pass_count': sum(1 for _, _, rc in generated if rc in (0, 2)),
        'fail_count': sum(1 for _, _, rc in generated if rc not in (0, 2)),
    }
    path = out_dir / f'{stem}-manifest.json'
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--bc-map')
    parser.add_argument('--max-tables', type=int, default=0,
                        help='Max tables per diagram before recursive splitting (0=use default threshold)')
    args = parser.parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    bc_map_path = Path(args.bc_map) if args.bc_map else Path(f'projects/{args.project}/outputs/asis/bounded-context-map.md')
    if not input_path.exists():
        print(f'ERROR: Input not found: {input_path}', file=sys.stderr)
        sys.exit(1)
    bcs = parse_bc_map(bc_map_path)
    exact, prefix_list, token_pairs = build_table_index(bcs)
    total_kt = sum(len(i['key_tables']) for i in bcs.values())
    print(f'[gen_er_diagram] BC map: {len(bcs)} BCs, {total_kt} key tables, {len(token_pairs)} tokens')
    with open(input_path, encoding='utf-8') as fh:
        payload = json.load(fh).get('payload', {})
    tables = payload.get('inferred_tables', []) + payload.get('tables', [])
    if not tables:
        print('ERROR: No tables', file=sys.stderr)
        sys.exit(1)
    # DEDUPLICATE: prefer DDL tables (with columns) over inferred tables
    tables_by_name: dict[str, any] = {}
    for t in tables:
        name = t.get('name', '').upper()
        if not name:
            continue
        existing = tables_by_name.get(name)
        if existing is None:
            tables_by_name[name] = t
            continue
        # Heuristic: keep the version with more column metadata
        existing_cols = len(existing.get('columns', []))
        new_cols = len(t.get('columns', []))
        if new_cols > existing_cols:
            tables_by_name[name] = t
    tables = list(tables_by_name.values())
    print(f'[gen_er_diagram] Deduplicated to {len(tables)} unique tables')
    prefix_groups = compute_prefix_groups(tables)
    domain_groups = defaultdict(list)
    for t in tables:
        name = t.get('name', '')
        if name:
            domain_groups[classify_table(name, exact, prefix_list, token_pairs, prefix_groups)].append(t)
    classified = sum(len(v) for g, v in domain_groups.items() if not g.startswith('Prefix:') and g != 'Other')
    print(f'[gen_er_diagram] {len(tables)} tables, {len(domain_groups)} groups, {classified} classified by BC')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    validator = Path('src/shared/utils/validate_diagram.py')
    generated = []
    overview = generate_overview(domain_groups, len(tables))
    rc = validate_and_write(overview, output_path, validator)
    generated.append((output_path.name, len(overview), rc))
    stem = output_path.stem
    out_dir = output_path.parent
    for g_label in sorted(domain_groups.keys()):
        items = domain_groups[g_label]
        g_slug = slugify(g_label)
        generate_recursive_details(
            items, g_label, g_slug, level=1, stem=stem, out_dir=out_dir,
            validator=validator, generated=generated,
            threshold=RECURSIVE_SUBGROUP_THRESHOLD,
            max_levels=MAX_RECURSIVE_LEVELS,
            max_tables=args.max_tables,
        )

    # Manifest with generated files
    write_manifest(out_dir, stem, len(tables), generated)

    print(f'[gen_er_diagram] Generated {len(generated)} files:')
    for name, size, rc in generated:
        status = 'PASS' if rc in (0, 2) else 'FAIL'
        print(f'  [{status}] {name} ({size:,} chars)')
    sys.exit(0 if all(r in (0, 2) for _, _, r in generated) else 1)


if __name__ == '__main__':
    main()
