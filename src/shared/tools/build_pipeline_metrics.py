#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Reconstrói pipeline-runner-metrics.json a partir dos artefatos do pipeline_runner.

O runner não emite esse arquivo: ele grava `runner-state.json` (métricas exatas da
última execução), `execution-report_*.md` (tabela por fase, resolução de 0.1 min) e
um relatório `.md` por fase cujo timestamp de nome é o instante em que a fase
terminou. Este script lê essas três fontes, concilia e escreve o JSON consolidado.

Precedência por fase:
  1. runner-state.json / runner-state-done.json  -> elapsed_s e tokens exatos
  2. tabela dos execution-report_*.md            -> fallback (Tempo em 0.1 min)
  3. timestamp do .md da fase                    -> fim real; início = fim - duração

Uso:
    # pasta com vários projetos, cada um com outputs/pipeline_runner
    python build_pipeline_metrics.py --root C:\\...\\Executions

    # um único projeto
    python build_pipeline_metrics.py --project C:\\...\\projects\\cadastro-funcionarios

    # .zip são lidos sem extrair; o JSON vai para --out-dir (nunca dentro do .zip)
    python build_pipeline_metrics.py --root C:\\...\\Executions --out-dir .\\metrics

Sem dependências externas.
"""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import json
import os
import re
import sys
import zipfile
from collections import OrderedDict

RUNNER_DIR = ("outputs", "pipeline_runner")
OUT_NAME = "pipeline-runner-metrics.json"
UTC = dt.timezone.utc

# nome de arquivo de fase: {fase}_{agente}_{YYYYMMDD}_{HHMMSS}.md
RE_PHASE_FILE = re.compile(r"^(?P<phase>[^_]+)_(?P<agent>.+)_(?P<d>\d{8})_(?P<t>\d{6})\.md$")
RE_REPORT_FILE = re.compile(r"^execution-report_(?P<d>\d{8})_(?P<t>\d{6})\.md$")
RE_DASH = re.compile(r"^[\s\u2014\u2013-]*$")  # célula vazia: "—", "-", " "


# --------------------------------------------------------------------------- #
# leitura de fontes (funciona igual para pasta e para .zip)
# --------------------------------------------------------------------------- #
class Source(object):
    """Acesso uniforme aos arquivos de um outputs/pipeline_runner."""

    def __init__(self, project, listing, reader, writable_dir=None, origin=None):
        self.project = project
        self.listing = listing          # [nome de arquivo]
        self._reader = reader           # nome -> bytes
        self.writable_dir = writable_dir
        self.origin = origin            # nome do .zip, quando veio de um arquivo
        self.solo_in_archive = True

    def read_text(self, name):
        raw = self._reader(name)
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")


def long_path(path):
    r"""Windows corta caminhos em 260 chars; o prefixo \\?\ remove o limite."""
    if os.name != "nt":
        return path
    full = os.path.abspath(path)
    prefix = "\\\\?\\"
    return full if full.startswith(prefix) else prefix + full


def source_from_dir(path):
    runner = os.path.join(path, *RUNNER_DIR)
    if not os.path.isdir(runner):
        return None
    names = sorted(n for n in os.listdir(runner) if os.path.isfile(os.path.join(runner, n)))

    def reader(name):
        with open(os.path.join(runner, name), "rb") as fh:
            return fh.read()

    return Source(os.path.basename(os.path.normpath(path)), names, reader, runner)


def sources_from_zip(path):
    """Um .zip pode conter mais de um projeto; devolve um Source para cada."""
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise RuntimeError("zip ilegível: %s" % exc)

    marker = "/".join(RUNNER_DIR) + "/"
    buckets = {}
    for info in zf.infolist():
        if info.is_dir():
            continue
        norm = info.filename.replace("\\", "/")
        if marker not in norm:
            continue
        prefix, _, leaf = norm.rpartition("/")
        if not leaf:
            continue
        buckets.setdefault(prefix, []).append((leaf, info.filename))

    stem = os.path.splitext(os.path.basename(path))[0]
    out = []
    for prefix in sorted(buckets):
        entries = dict(buckets[prefix])
        root = prefix.split("/")[0] or stem
        out.append(Source(root, sorted(entries), lambda n, e=entries, z=zf: z.read(e[n]),
                          origin=stem))
    for src in out:
        src.solo_in_archive = len(out) == 1
    return out


# --------------------------------------------------------------------------- #
# parsing
# --------------------------------------------------------------------------- #
def stamp_to_utc(day, tod, tz_offset_hours):
    """'20260826' + '114531' (hora local da máquina do runner) -> datetime UTC."""
    local = dt.datetime.strptime(day + tod, "%Y%m%d%H%M%S")
    return local.replace(tzinfo=UTC) - dt.timedelta(hours=tz_offset_hours)


def parse_number(cell):
    cell = cell.strip().replace(",", "").replace(".", "") if cell else ""
    return int(cell) if cell.isdigit() else None


def parse_elapsed(cell):
    """'8.4m' | '0s' | '1.2h' -> segundos."""
    cell = (cell or "").strip()
    m = re.match(r"^([\d.]+)\s*(s|m|h)$", cell)
    if not m:
        return None
    val, unit = float(m.group(1)), m.group(2)
    return val * {"s": 1.0, "m": 60.0, "h": 3600.0}[unit]


def parse_execution_report(text):
    """Extrai a tabela 'Uso de Contexto por Fase' e as listas de status."""
    rows = OrderedDict()
    status_lists = {}

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]

        # blocos de Resultado: "| ✅ Executadas | 15 — F0, F1, ... |"
        if len(cells) == 2 and "—" in cells[1]:
            label = cells[0].lower()
            _, _, tail = cells[1].partition("—")
            names = [p.strip() for p in tail.split(",") if p.strip() and not RE_DASH.match(p)]
            for key, token in (("executed", "executad"), ("skipped", "pulad"),
                               ("val_failed", "val-fail"), ("aborted", "abortad")):
                if token in label:
                    status_lists[key] = names
            continue

        # tabela por fase: 10 colunas
        if len(cells) != 10:
            continue
        phase = cells[0]
        if (not phase or phase.lower().startswith("fase") or "TOTAL" in phase
                or set(phase) <= set("-: ")):
            continue
        rows[phase.strip("*` ")] = {
            "agent": cells[1],
            "token_in": parse_number(cells[3]),
            "token_out": parse_number(cells[4]),
            "duration_seconds": parse_elapsed(cells[7]),
        }
    return rows, status_lists


def load_runner_states(src):
    """Funde runner-state*.json; o mais recente vence por fase."""
    states = []
    for name in src.listing:
        if not (name.startswith("runner-state") and name.endswith(".json")):
            continue
        try:
            states.append(json.loads(src.read_text(name)))
        except ValueError:
            continue
    states.sort(key=lambda s: s.get("saved_at") or "")

    merged = {"exec_metrics": {}, "executed": [], "degraded": [], "skipped": [],
              "aborted": [], "val_failed": [], "saved_at": None, "run_id": None,
              "project": None}
    for st in states:
        merged["exec_metrics"].update(st.get("exec_metrics") or {})
        for phase in st.get("executed") or []:
            if phase not in merged["executed"]:
                merged["executed"].append(phase)
        for key in ("degraded", "skipped", "aborted", "val_failed"):
            merged[key].extend(st.get(key) or [])
        for key in ("saved_at", "run_id", "project"):
            if st.get(key):
                merged[key] = st[key]
    return merged if states else None


def load_reports(src, tz):
    """Funde as tabelas de todos os execution-report.

    Runs retomados gravam um relatório novo contendo APENAS as fases reexecutadas;
    as demais aparecem zeradas ou como '—'. Por isso a fusão é "a última vez em que
    a fase de fato rodou": só sobrescreve quando a linha nova traz números, e o
    status vem do mesmo relatório que forneceu os números — nunca da lista de
    'Puladas' de um resume posterior, que não diz nada sobre a execução original.
    """
    reports = []
    for name in src.listing:
        m = RE_REPORT_FILE.match(name)
        if m:
            reports.append((stamp_to_utc(m.group("d"), m.group("t"), tz), name))
    reports.sort()

    rows, phase_status, order, last = OrderedDict(), {}, [], None
    superseded = [0, 0]        # [fases reexecutadas, tokens das execuções anteriores]
    for when, name in reports:
        table, lists = parse_execution_report(src.read_text(name))

        declared = {}
        for key, names in lists.items():
            for phase in names:
                declared[phase] = key

        for phase, data in table.items():
            has_data = data["token_in"] is not None or data["duration_seconds"] is not None
            if has_data or phase not in rows:
                old = rows.get(phase)
                if old and has_data:
                    spent = (old["token_in"] or 0) + (old["token_out"] or 0)
                    if spent:
                        superseded[0] += 1
                        superseded[1] += spent
                rows[phase] = data
                phase_status[phase] = declared.get(phase, "executed")

        # fases citadas só nas listas de status, sem linha na tabela
        for phase, key in declared.items():
            if phase not in rows:
                rows[phase] = {"agent": None, "token_in": None,
                               "token_out": None, "duration_seconds": None}
                phase_status[phase] = key

        for phase in list(lists.get("executed") or []) + list(table):
            if phase not in order:
                order.append(phase)
        last = when
    return rows, phase_status, order, last, superseded


def index_phase_files(src, tz):
    """fase (forma de arquivo) -> [datetime UTC de término], em ordem."""
    idx = {}
    for name in src.listing:
        m = RE_PHASE_FILE.match(name)
        if not m:
            continue
        idx.setdefault(m.group("phase"), []).append(stamp_to_utc(m.group("d"), m.group("t"), tz))
    for key in idx:
        idx[key].sort()
    return idx


# --------------------------------------------------------------------------- #
# montagem
# --------------------------------------------------------------------------- #
def hms(seconds):
    s = int(round(seconds))
    return "%02d:%02d:%02d" % (s // 3600, (s % 3600) // 60, s % 60)


def round_dt(when):
    """Arredonda para o segundo — os timestamps de origem têm essa resolução."""
    return (when + dt.timedelta(seconds=0.5)).replace(microsecond=0) if when else None


def iso_z(when):
    return round_dt(when).strftime("%Y-%m-%dT%H:%M:%SZ") if when else ""


def build_metrics(src, tz, forced_status=None):
    state = load_runner_states(src)
    rows, report_status, report_order, report_when, superseded = load_reports(src, tz)
    files = index_phase_files(src, tz)
    notes = []

    exec_metrics = (state or {}).get("exec_metrics") or {}
    degraded = {d.get("phase") for d in (state or {}).get("degraded") or [] if isinstance(d, dict)}
    degraded |= set((state or {}).get("val_failed") or [])

    declared = list(report_order)
    for phase in list((state or {}).get("executed") or []) + list(rows) + list(exec_metrics):
        if phase not in declared:
            declared.append(phase)
    if not declared:
        raise RuntimeError("nenhuma fase encontrada")

    # Ordena cronologicamente pelo fim real de cada fase. Um projeto retomado várias
    # vezes tem listas 'executed' que não seguem o relógio, e o encadeamento
    # início = fim - duração só faz sentido em ordem cronológica.
    def end_of(phase):
        stamps = files.get(phase.replace(":", "-")) or []
        if report_when:
            usable = [s for s in stamps if s <= report_when + dt.timedelta(minutes=1)]
            stamps = usable or stamps
        return stamps[-1] if stamps else None

    ends_by_phase, keyed, carry = {}, [], None
    for idx, phase in enumerate(declared):
        end = end_of(phase)
        ends_by_phase[phase] = end
        if end is not None:
            carry = end
        # fase sem relatório (tools determinísticas) fica logo após a última datada
        keyed.append(((carry or dt.datetime.min.replace(tzinfo=UTC)), idx, phase))
    order = [phase for _, _, phase in sorted(keyed)]

    phases, prev_end = [], None
    for phase in order:
        em = exec_metrics.get(phase) or {}
        row = rows.get(phase) or {}

        duration = em.get("elapsed_s")
        exact = duration is not None          # runner-state mede em ms; relatório, em 0.1 min
        if duration is None:
            duration = row.get("duration_seconds")
        duration = float(duration or 0.0)

        token_in = em.get("inp_tokens")
        if token_in is None:
            token_in = row.get("token_in")
        token_out = em.get("resp_tokens")
        if token_out is None:
            token_out = row.get("token_out")
        token_in, token_out = int(token_in or 0), int(token_out or 0)

        end = ends_by_phase.get(phase)
        start = end - dt.timedelta(seconds=duration) if (end and duration) else None

        # 'Tempo' do relatório tem resolução de 0.1 min e pode gerar sobreposição.
        # Só reajusta quando a duração é aproximada — a medida do runner-state é
        # a fonte da verdade e nunca é reescrita a partir de timestamps.
        if start and prev_end and start < prev_end:
            overlap = (prev_end - start).total_seconds()
            if not exact and overlap <= 5:
                start, duration = prev_end, (end - prev_end).total_seconds()
            elif overlap >= 1:
                notes.append("%s inicia %.0fs antes do fim da fase anterior" % (phase, overlap))
        if end:
            prev_end = end

        declared_st = report_status.get(phase)
        if phase in degraded or declared_st == "val_failed":
            st = "degraded"
        elif declared_st in ("skipped", "aborted"):
            st = declared_st
        else:
            st = "executed"

        phases.append(OrderedDict([
            ("phase_name", phase),
            ("status", st),
            ("start_time_utc", iso_z(start)),
            ("end_time_utc", iso_z(end)),
            ("duration_seconds", round(duration, 3)),
            ("total_hours", hms(duration)),
            ("token_usage", OrderedDict([
                ("total_tokens", token_in + token_out),
                ("token_in", token_in),
                ("token_out", token_out),
            ])),
        ]))

    # janela do run: início da primeira fase medida -> saved_at do state (ou último fim)
    starts = [p["start_time_utc"] for p in phases if p["start_time_utc"]]
    ends = [p["end_time_utc"] for p in phases if p["end_time_utc"]]
    if not starts:
        raise RuntimeError("nenhuma fase com horário reconstruível")
    run_start = dt.datetime.strptime(min(starts), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)

    run_end = None
    if state and state.get("saved_at"):
        try:
            saved = state["saved_at"][:26]
            fmt = "%Y-%m-%dT%H:%M:%S.%f" if "." in saved else "%Y-%m-%dT%H:%M:%S"
            saved_dt = dt.datetime.strptime(saved, fmt).replace(tzinfo=UTC)
            saved_dt = saved_dt - dt.timedelta(hours=tz)
            run_end = (saved_dt + dt.timedelta(seconds=0.5)).replace(microsecond=0)
        except ValueError:
            pass
    last_end = dt.datetime.strptime(max(ends), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC) if ends else None
    if run_end is None or (last_end and last_end > run_end):
        run_end = last_end
    if run_end is None or run_end < run_start:
        run_end = run_start

    total = (run_end - run_start).total_seconds()

    seen = {p["status"] for p in phases}
    if forced_status:
        exec_status = forced_status
    elif "aborted" in seen:
        exec_status = "aborted"
    elif "degraded" in seen or "skipped" in seen:
        exec_status = "completed_with_warnings"
    else:
        exec_status = "completed"

    token_in = sum(p["token_usage"]["token_in"] for p in phases)
    token_out = sum(p["token_usage"]["token_out"] for p in phases)

    doc = OrderedDict([
        ("execution_id", "runner19-%d" % calendar.timegm(run_start.utctimetuple())),
        ("project_name", (state or {}).get("project") or src.project),
        ("execution_mode", "full"),
        ("execution_status", exec_status),
        ("start_time_utc", iso_z(run_start)),
        ("end_time_utc", iso_z(run_end)),
        ("total_duration_seconds", round(total, 3)),
        ("total_hours", hms(total)),
        ("token_metrics", OrderedDict([
            ("total_tokens", token_in + token_out),
            ("token_in", token_in),
            ("token_out", token_out),
        ])),
        ("phase_metrics", phases),
    ])

    if superseded[0]:
        notes.append("%d fase(s) reexecutada(s): %s tokens de execuções anteriores não "
                     "entram no total (cada fase conta a última vez que rodou)"
                     % (superseded[0], format(superseded[1], ",d").replace(",", ".")))

    stats = {
        "phases": len(phases),
        "superseded_phases": superseded[0],
        "superseded_tokens": superseded[1],
        "no_telemetry": sum(1 for p in phases
                            if p["status"] == "executed" and p["duration_seconds"] == 0
                            and p["token_usage"]["total_tokens"] == 0),
        "degraded": sum(1 for p in phases if p["status"] == "degraded"),
        "source": "runner-state" if exec_metrics else "execution-report",
        "notes": notes,
    }
    return doc, stats


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def discover(root):
    """Devolve [(rótulo, [Source]), ...] para pastas de projeto e .zip sob root."""
    found = []
    for entry in sorted(os.listdir(root)):
        path = os.path.join(root, entry)
        if os.path.isdir(path):
            src = source_from_dir(path)
            if src:
                found.append((entry, [src], None))
        elif entry.lower().endswith(".zip"):
            try:
                srcs = sources_from_zip(path)
            except RuntimeError as exc:
                found.append((entry, [], str(exc)))
                continue
            if srcs:
                found.append((entry, srcs, None))
        elif entry.lower().endswith((".7z", ".rar")):
            found.append((entry, [], "formato não suportado pela stdlib — extraia antes"))
    return found


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Reconstrói pipeline-runner-metrics.json a partir dos artefatos do pipeline_runner.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--root", help="pasta com vários projetos (subpastas e/ou .zip)")
    g.add_argument("--project", help="pasta de um único projeto (contendo outputs/pipeline_runner)")
    ap.add_argument("--out-dir", help="destino dos JSON; padrão: o próprio outputs/pipeline_runner "
                                      "(projetos em .zip sempre exigem --out-dir)")
    ap.add_argument("--tz-offset-hours", type=float, default=-3.0,
                    help="fuso da máquina que gerou os artefatos (padrão: -3, Brasília)")
    ap.add_argument("--status", help="força execution_status em vez de derivá-lo")
    ap.add_argument("--overwrite", action="store_true", help="sobrescreve JSON já existente")
    ap.add_argument("--dry-run", action="store_true", help="calcula e resume, sem gravar")
    ap.add_argument("--summary-json", help="grava um resumo consolidado de todos os projetos")
    args = ap.parse_args(argv)

    if args.project:
        src = source_from_dir(args.project)
        if not src:
            ap.error("%s não contém outputs/pipeline_runner" % args.project)
        targets = [(os.path.basename(os.path.normpath(args.project)), [src], None)]
    else:
        if not os.path.isdir(args.root):
            ap.error("--root não é uma pasta: %s" % args.root)
        targets = discover(args.root)

    summary, failures = [], 0
    for label, sources, problem in targets:
        if problem:
            print("  ~  %-52s %s" % (label, problem))
            continue
        for src in sources:
            tag = label if len(sources) == 1 else "%s :: %s" % (label, src.project)
            try:
                doc, stats = build_metrics(src, args.tz_offset_hours, args.status)
            except Exception as exc:               # noqa: BLE001 - relatado por projeto
                print("  !  %-52s FALHOU: %s" % (tag, exc))
                failures += 1
                continue

            if args.out_dir:
                if src.origin:
                    # uma subpasta por arquivo (dois .zip podem trazer o mesmo projeto);
                    # o nome do projeto só entra quando o arquivo traz mais de um
                    parts = [args.out_dir, src.origin]
                    if not getattr(src, "solo_in_archive", True):
                        parts.append(doc["project_name"])
                else:
                    parts = [args.out_dir, doc["project_name"]]
                dest_dir = os.path.join(*parts)
            elif src.writable_dir:
                dest_dir = src.writable_dir
            else:
                print("  !  %-52s dentro de .zip — informe --out-dir" % tag)
                failures += 1
                continue
            dest = os.path.join(dest_dir, OUT_NAME)

            exists = os.path.exists(long_path(dest))
            if exists and not args.overwrite and not args.dry_run:
                print("  ~  %-52s já existe (use --overwrite)" % tag)
                continue

            if not args.dry_run:
                if not os.path.isdir(long_path(dest_dir)):
                    os.makedirs(long_path(dest_dir))
                with open(long_path(dest), "w", encoding="utf-8") as fh:
                    json.dump(doc, fh, indent=2, ensure_ascii=False)
                    fh.write("\n")

            print("  %s %-52s %2d fases · %s · %s tokens · fonte: %s%s" % (
                "·" if args.dry_run else "OK", tag, stats["phases"], doc["total_hours"],
                format(doc["token_metrics"]["total_tokens"], ",d").replace(",", "."),
                stats["source"],
                " · %d sem telemetria" % stats["no_telemetry"] if stats["no_telemetry"] else ""))
            for note in stats["notes"]:
                print("       aviso: %s" % note)

            summary.append({
                "project_name": doc["project_name"],
                "archive": label,
                "output": None if args.dry_run else dest,
                "execution_id": doc["execution_id"],
                "execution_status": doc["execution_status"],
                "start_time_utc": doc["start_time_utc"],
                "end_time_utc": doc["end_time_utc"],
                "total_duration_seconds": doc["total_duration_seconds"],
                "token_metrics": doc["token_metrics"],
                "phases": stats["phases"],
                "degraded": stats["degraded"],
                "no_telemetry": stats["no_telemetry"],
                "source": stats["source"],
            })

    if args.summary_json and not args.dry_run:
        with open(long_path(args.summary_json), "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print("\nresumo consolidado: %s" % args.summary_json)

    total_tokens = sum(s["token_metrics"]["total_tokens"] for s in summary)
    print("\n%d projeto(s) · %s tokens no total%s" % (
        len(summary), format(total_tokens, ",d").replace(",", "."),
        " · %d falha(s)" % failures if failures else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
