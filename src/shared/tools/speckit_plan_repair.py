#!/usr/bin/env python3
"""Recupera plan-graph.json incompleto usando o task-fragment.json como fonte.

Ferramenta de RECUPERAÇÃO, irmã de ``reconstruct_runner_state.py``. Não faz parte
do fluxo normal: no fluxo normal o ``plan-graph.json`` é a autoridade e o gate
``speckit-plan-validate`` (F3S wave4a) impede que um plano incoerente chegue à
wave5.

Ela existe para o caso já materializado: o agente de planning declarou um grupo
na seção 3 sem enumerar os arquivos dele na seção 4, e o agente de tasks — sem
ownership para aquele grupo — criou as tasks assim mesmo. O resultado é um
fragment MAIS completo que o plano, e o compilador reprova.

Que o fragment está certo e o plano incompleto não é suposição: o próprio plano
declara ``consumes`` de tokens que só os arquivos ausentes produzem. Ver
``docs/issues/ISSUE-004-speckit-plan-graph-perda-silenciosa.md`` §7.

Uso:
    python src/shared/tools/speckit_plan_repair.py --project <nome>            # dry-run
    python src/shared/tools/speckit_plan_repair.py --project <nome> --apply
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]

# Campos de arquivo que o plano precisa e que o fragment já carrega.
_CAMPOS = ("action", "group", "task_type", "source_refs", "produces", "consumes")


class RepairError(ValueError):
    """Erro fatal do reparo; o CLI trata como exit 2."""


def _specs_dir(project: str, root: Path) -> Path:
    return root / "projects" / project / "outputs" / "tobe" / "speckit" / "specs"


def _write_atomic(path: Path, content: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def _linha_de_arquivo(entry: dict[str, Any]) -> dict[str, Any]:
    """Converte uma entry do fragment na linha de `files` do plano."""
    return {
        "path": entry["target_file"],
        "action": entry.get("action"),
        "group": entry.get("group"),
        "task_type": entry.get("task_type"),
        # `responsibility` é do plano; o fragment tem `title`, que é o
        # equivalente mais próximo. Marcado para auditoria.
        "responsibility": entry.get("title") or "(derivado do task-fragment)",
        "source_refs": entry.get("source_refs") or [],
        "produces": entry.get("produces") or [],
        "consumes": entry.get("consumes") or [],
    }


def repair_project(project: str, repo_root: Path | None = None,
                   *, apply: bool = False) -> dict[str, Any]:
    """Injeta no plano os arquivos que só existem no fragment.

    Nunca remove nem altera linha existente do plano — só acrescenta o que falta.
    """
    root = repo_root or REPO_ROOT
    specs = _specs_dir(project, root)
    if not specs.is_dir():
        raise RepairError(f"diretório de specs não encontrado: {specs}")

    relatorio: list[dict[str, Any]] = []
    for feature_dir in sorted(p for p in specs.iterdir() if p.is_dir()):
        plano_path = feature_dir / "plan-graph.json"
        frag_path = feature_dir / "task-fragment.json"
        if not (plano_path.is_file() and frag_path.is_file()):
            continue
        plano = json.loads(plano_path.read_text(encoding="utf-8"))
        frag = json.loads(frag_path.read_text(encoding="utf-8"))

        existentes = {str(f.get("path")) for f in plano.get("files") or []}
        grupos = {str(g.get("group")) for g in plano.get("groups") or []}
        novos: list[dict[str, Any]] = []
        recusados: list[str] = []
        for entry in frag.get("entries") or []:
            alvo = str(entry.get("target_file") or "")
            if not alvo or alvo in existentes:
                continue
            faltando = [c for c in _CAMPOS if entry.get(c) in (None, "", [])]
            # `produces`/`consumes` vazios são legítimos; os demais, não.
            faltando = [c for c in faltando if c not in ("produces", "consumes")]
            if faltando:
                recusados.append(f"{alvo} (sem {', '.join(faltando)})")
                continue
            if str(entry.get("group")) not in grupos:
                recusados.append(f"{alvo} (grupo {entry.get('group')} não declarado no plano)")
                continue
            existentes.add(alvo)
            novos.append(_linha_de_arquivo(entry))

        if not novos and not recusados:
            continue
        item = {
            "feature": feature_dir.name,
            "arquivos_no_plano_antes": len(plano.get("files") or []),
            "injetados": len(novos),
            "recusados": recusados,
            "grupos_preenchidos": sorted({str(f["group"]) for f in novos}),
            "paths": [f["path"] for f in novos],
        }
        relatorio.append(item)

        if apply and novos:
            plano.setdefault("files", []).extend(novos)
            _write_atomic(plano_path,
                          json.dumps(plano, ensure_ascii=False, indent=2) + "\n")

    return {
        "project": project,
        "applied": apply,
        "features_afetadas": len(relatorio),
        "total_injetados": sum(i["injetados"] for i in relatorio),
        "total_recusados": sum(len(i["recusados"]) for i in relatorio),
        "detalhe": relatorio,
    }


def repair_orphan_contracts(project: str, repo_root: Path | None = None,
                            *, apply: bool = False) -> dict[str, Any]:
    """Declara `contract:X` no arquivo que É o X, quando alguém o consome.

    Caso observado: `ProductsController.cs` declara `consumes: contract:CatalogService`,
    e `CatalogService.cs` está no plano mas só declara produzir seus `api:*`. O
    consumo fica órfão (P002) e o compilador aborta, embora o produtor exista.

    O token `contract:X` nomeia a classe; o arquivo `X.cs` é o produtor
    inequívoco. Só age quando existe exatamente UM arquivo com esse stem no
    plano da feature — havendo ambiguidade, recusa e reporta.
    """
    root = repo_root or REPO_ROOT
    specs = _specs_dir(project, root)
    relatorio: list[dict[str, Any]] = []

    for feature_dir in sorted(p for p in specs.iterdir() if p.is_dir()):
        plano_path = feature_dir / "plan-graph.json"
        if not plano_path.is_file():
            continue
        plano = json.loads(plano_path.read_text(encoding="utf-8"))
        arquivos = plano.get("files") or []
        produzidos = {t for f in arquivos for t in (f.get("produces") or [])}
        consumidos = {t for f in arquivos for t in (f.get("consumes") or [])}

        por_stem: dict[str, list[dict[str, Any]]] = {}
        for f in arquivos:
            stem = Path(str(f.get("path"))).stem
            por_stem.setdefault(stem, []).append(f)

        adicionados: list[str] = []
        recusados: list[str] = []
        for token in sorted(consumidos - produzidos):
            if not token.startswith("contract:"):
                recusados.append(f"{token} (não é contract:)")
                continue
            nome = token.split(":", 1)[1]
            candidatos = por_stem.get(nome, [])
            if len(candidatos) != 1:
                recusados.append(
                    f"{token} ({len(candidatos)} arquivo(s) com stem {nome!r})")
                continue
            alvo = candidatos[0]
            alvo.setdefault("produces", []).append(token)
            adicionados.append(f"{token} → {Path(str(alvo['path'])).name}")

        if not adicionados and not recusados:
            continue
        relatorio.append({
            "feature": feature_dir.name,
            "adicionados": len(adicionados),
            "detalhe": adicionados,
            "recusados": recusados,
        })
        if apply and adicionados:
            _write_atomic(plano_path,
                          json.dumps(plano, ensure_ascii=False, indent=2) + "\n")

    return {
        "project": project,
        "applied": apply,
        "total_adicionados": sum(i["adicionados"] for i in relatorio),
        "total_recusados": sum(len(i["recusados"]) for i in relatorio),
        "detalhe": relatorio,
    }


def repair_dead_refs(project: str, repo_root: Path | None = None,
                     *, apply: bool = False) -> dict[str, Any]:
    """Remove `source_refs` cuja âncora não existe no artefato-fonte.

    Não é maquiagem de check: uma âncora que não resolve é uma citação para o
    vazio, e apagá-la **aumenta** a exatidão da rastreabilidade. O que sobra
    passa a ser inteiramente verificável.

    Guarda-corpo essencial: só remove se restar pelo menos UMA referência válida
    naquele arquivo. Se a inválida for a única, o arquivo ficaria sem
    rastreabilidade alguma — aí o defeito é de conteúdo e exige decisão humana
    (a decisão citada não existe: ela faltou na constituição, ou a citação está
    errada?). Nesse caso a ferramenta recusa e reporta.
    """
    root = repo_root or REPO_ROOT
    specs = _specs_dir(project, root)
    sys.path.insert(0, str(SCRIPT_DIR))
    import speckit_task_compiler as compilador  # noqa: PLC0415

    cache: dict[str, tuple[str, set[str]]] = {}
    proj = root / "projects" / project
    relatorio: list[dict[str, Any]] = []

    for feature_dir in sorted(p for p in specs.iterdir() if p.is_dir()):
        plano_path = feature_dir / "plan-graph.json"
        if not plano_path.is_file():
            continue
        plano = json.loads(plano_path.read_text(encoding="utf-8"))
        removidos: list[str] = []
        recusados: list[str] = []
        for item in plano.get("files") or []:
            refs = item.get("source_refs") or []
            validas, invalidas = [], []
            for ref in refs:
                rel = str(ref.get("artifact") or "")
                if rel not in cache:
                    alvo = proj / rel
                    if not alvo.is_file():
                        alvo = root / rel
                    texto = alvo.read_text(encoding="utf-8", errors="replace") \
                        if alvo.is_file() else ""
                    cache[rel] = (texto, compilador._headings_slug(texto))
                texto, slugs = cache[rel]
                destino = (validas if compilador._ancora_resolve(
                    str(ref.get("anchor") or ""), texto, slugs) else invalidas)
                destino.append(ref)
            if not invalidas:
                continue
            nome = Path(str(item.get("path"))).name
            if not validas:
                recusados.append(
                    f"{nome}: {[r.get('anchor') for r in invalidas]} é a única "
                    f"referência — exige decisão de conteúdo")
                continue
            item["source_refs"] = validas
            removidos.extend(f"{nome}: {r.get('anchor')}" for r in invalidas)

        if not removidos and not recusados:
            continue
        relatorio.append({
            "feature": feature_dir.name,
            "removidos": len(removidos),
            "detalhe": removidos,
            "recusados": recusados,
        })
        if apply and removidos:
            _write_atomic(plano_path,
                          json.dumps(plano, ensure_ascii=False, indent=2) + "\n")

    return {
        "project": project,
        "applied": apply,
        "total_removidos": sum(i["removidos"] for i in relatorio),
        "total_recusados": sum(len(i["recusados"]) for i in relatorio),
        "detalhe": relatorio,
    }


def repair_duplicate_task_ids(project: str, repo_root: Path | None = None,
                              *, apply: bool = False) -> dict[str, Any]:
    """Desambigua `task_id` repetido entre fragments, reescrevendo as referências.

    O agente de tasks usa prefixos não escopados por feature para trabalho
    transversal (`T-TST-*`, `T-HOST-*`), então duas waves geram a mesma sequência
    de forma independente. O `task_id` precisa ser único no conjunto — é a chave
    do ledger e do grafo global.

    Mantém o id na feature de menor ordem (a que aparece primeiro) e renomeia na
    seguinte, inserindo o id da wave como discriminador: `T-TST-001` da wave W2
    vira `T-W2-TST-001`. `depends_on` que apontem para o id antigo dentro da
    mesma feature são reescritos junto.
    """
    root = repo_root or REPO_ROOT
    specs = _specs_dir(project, root)

    fragmentos: list[tuple[str, Path, dict[str, Any]]] = []
    for feature_dir in sorted(p for p in specs.iterdir() if p.is_dir()):
        frag_path = feature_dir / "task-fragment.json"
        if frag_path.is_file():
            fragmentos.append((feature_dir.name, frag_path,
                               json.loads(frag_path.read_text(encoding="utf-8"))))

    vistos: dict[str, str] = {}       # task_id -> feature que ficou com ele
    relatorio: list[dict[str, Any]] = []
    for feature, frag_path, frag in fragmentos:
        wave = str(frag.get("migration_wave_id") or "").strip()
        renomes: dict[str, str] = {}
        for entry in frag.get("entries") or []:
            tid = str(entry.get("task_id") or "")
            if tid not in vistos:
                vistos[tid] = feature
                continue
            if not wave:
                continue                        # sem discriminador seguro
            novo = tid.replace("T-", f"T-{wave}-", 1)
            sufixo = 1
            while novo in vistos:
                sufixo += 1
                novo = tid.replace("T-", f"T-{wave}{sufixo}-", 1)
            renomes[tid] = novo
            vistos[novo] = feature

        if not renomes:
            continue
        for entry in frag.get("entries") or []:
            tid = str(entry.get("task_id") or "")
            if tid in renomes:
                entry["task_id"] = renomes[tid]
            dep = entry.get("depends_on") or []
            if any(d in renomes for d in dep):
                entry["depends_on"] = [renomes.get(d, d) for d in dep]

        relatorio.append({
            "feature": feature,
            "renomeados": len(renomes),
            "de_para": [f"{a} → {b}" for a, b in sorted(renomes.items())],
        })
        if apply:
            _write_atomic(frag_path,
                          json.dumps(frag, ensure_ascii=False, indent=2) + "\n")

    return {
        "project": project,
        "applied": apply,
        "total_renomeados": sum(i["renomeados"] for i in relatorio),
        "detalhe": relatorio,
    }


def repair_ownership(project: str, repo_root: Path | None = None,
                     *, apply: bool = False) -> dict[str, Any]:
    """Converte `create` duplicado em `update` na wave que NÃO é dona do arquivo.

    Só age onde a decisão é **confiável**: quando exatamente uma spec declara o
    arquivo no escopo funcional da wave, ela é a dona e as demais viram
    `update`. Conflito de owner indeterminado é deixado como está — resolver no
    escuro trocaria um defeito visível por uma decisão silenciosa (§3.5).

    Escreve nos DOIS artefatos, porque o compilador cruza um contra o outro: o
    `plan-graph.json` é a autoridade de ownership e o `task-fragment.json`
    carrega a `action` que o agente copiou de lá.

    Idempotente: rodar de novo não encontra mais nada a converter.
    """
    root = repo_root or REPO_ROOT
    specs = _specs_dir(project, root)
    sys.path.insert(0, str(SCRIPT_DIR))
    import speckit_task_compiler as compiler  # noqa: PLC0415

    planos: dict[str, dict[str, Any]] = {}
    caminhos: dict[str, Path] = {}
    for feature_dir in sorted(p for p in specs.iterdir() if p.is_dir()):
        plano = feature_dir / "plan-graph.json"
        if plano.is_file():
            caminhos[feature_dir.name] = plano
            planos[feature_dir.name] = json.loads(plano.read_text(encoding="utf-8"))

    spec_texts = compiler._spec_texts(specs, sorted(planos))
    conversoes: list[dict[str, Any]] = []
    indecisos: list[dict[str, Any]] = []

    for alvo, claims in sorted(compiler._claims_dos_planos(planos).items()):
        creates = [c for c in claims if c["action"] == "create"]
        if len(creates) < 2:
            continue
        dono, motivo = compiler.recommend_owner(alvo, creates, spec_texts)
        if not dono:
            indecisos.append({"target_file": alvo, "motivo": motivo,
                              "features": sorted({c["feature"] for c in creates})})
            continue
        for claim in creates:
            if claim["feature"] == dono:
                continue
            conversoes.append({
                "target_file": alvo, "feature": claim["feature"],
                "task_id": claim["task_id"], "owner": dono,
                "de": "create", "para": "update", "motivo": motivo,
            })

    # Aplica agrupando por feature: um write por arquivo, não um por conversão.
    por_feature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in conversoes:
        por_feature[c["feature"]].append(c)

    for feature, itens in sorted(por_feature.items()):
        alvos = {i["target_file"] for i in itens}
        plano = planos[feature]
        for arquivo in plano.get("files") or []:
            if compiler.normalize_target(arquivo.get("path")) in alvos:
                arquivo["action"] = "update"
        frag_path = specs / feature / "task-fragment.json"
        frag = (json.loads(frag_path.read_text(encoding="utf-8"))
                if frag_path.is_file() else None)
        if frag:
            for entry in frag.get("entries") or []:
                if compiler.normalize_target(entry.get("target_file")) in alvos:
                    entry["action"] = "update"
        if apply:
            _write_atomic(caminhos[feature],
                          json.dumps(plano, ensure_ascii=False, indent=2) + "\n")
            if frag:
                _write_atomic(frag_path,
                              json.dumps(frag, ensure_ascii=False, indent=2) + "\n")

    return {
        "project": project,
        "applied": apply,
        "total_convertidos": len(conversoes),
        "total_indecisos": len(indecisos),
        "features_afetadas": len(por_feature),
        "conversoes": conversoes,
        "indecisos": indecisos,
        "detalhe": [
            {"feature": feature, "renomeados": len(itens),
             "paths": [i["target_file"] for i in itens]}
            for feature, itens in sorted(por_feature.items())
        ],
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="speckit_plan_repair.py",
        description="Injeta no plan-graph.json os arquivos que só o task-fragment.json tem.")
    parser.add_argument("-p", "--project", required=True)
    parser.add_argument("--apply", action="store_true",
                        help="grava as alterações; sem esta flag é dry-run")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--mode", default="files",
        choices=["files", "orphan-contracts", "dead-refs", "duplicate-task-ids",
                 "ownership", "all"],
        help="files: injeta no plano os arquivos que só o fragment tem (padrão) · "
             "orphan-contracts: declara contract:X no arquivo que é o X · "
             "dead-refs: remove source_refs cuja âncora não existe na fonte · "
             "duplicate-task-ids: desambigua task_id repetido entre fragments · "
             "ownership: converte create duplicado em update na wave que a spec "
             "nao aponta como dona (so onde a decisao e confiavel) · "
             "all: todos, nessa ordem",
    )
    args = parser.parse_args(argv)

    modos = (["files", "orphan-contracts", "dead-refs", "duplicate-task-ids",
              "ownership"]
             if args.mode == "all" else [args.mode])
    fn = {"files": repair_project,
          "orphan-contracts": repair_orphan_contracts,
          "dead-refs": repair_dead_refs,
          "duplicate-task-ids": repair_duplicate_task_ids,
          "ownership": repair_ownership}

    resultados = {}
    try:
        for modo in modos:
            resultados[modo] = fn[modo](args.project, apply=args.apply)
    except (RepairError, OSError, json.JSONDecodeError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(resultados if len(resultados) > 1
                         else next(iter(resultados.values())),
                         ensure_ascii=False, indent=2))
        return 0

    if len(resultados) > 1 or args.mode != "files":
        modo_txt = "APLICADO" if args.apply else "DRY-RUN (use --apply para gravar)"
        print(f"Reparo SpecKit — {args.project} [{modo_txt}]")
        for modo, r in resultados.items():
            print(f"\n── modo: {modo}")
            for chave in ("total_injetados", "total_adicionados",
                          "total_removidos", "total_renomeados"):
                if chave in r:
                    print(f"   {chave.replace('total_', '')}: {r[chave]}")
            for item in r.get("detalhe", []):
                nome = item.get("feature", "?")
                linhas = (item.get("paths") or item.get("detalhe")
                          or item.get("de_para") or [])
                print(f"   {nome}: {len(linhas)} alteração(ões)")
                for x in linhas[:4]:
                    print(f"      {Path(str(x)).name if '/' in str(x) else x}")
                if len(linhas) > 4:
                    print(f"      … mais {len(linhas) - 4}")
                for x in item.get("recusados", []):
                    print(f"      ! recusado: {x}")
        return 0

    resultado = resultados["files"]

    modo = "APLICADO" if resultado["applied"] else "DRY-RUN (use --apply para gravar)"
    print(f"Reparo de plan-graph — {resultado['project']} [{modo}]")
    print(f"{resultado['total_injetados']} arquivo(s) a injetar em "
          f"{resultado['features_afetadas']} feature(s); "
          f"{resultado['total_recusados']} recusado(s)")
    for item in resultado["detalhe"]:
        print(f"\n── {item['feature']}: {item['arquivos_no_plano_antes']} "
              f"→ {item['arquivos_no_plano_antes'] + item['injetados']} arquivos")
        if item["grupos_preenchidos"]:
            print(f"   grupos preenchidos: {', '.join(item['grupos_preenchidos'])}")
        for path in item["paths"][:5]:
            print(f"     + {path}")
        if len(item["paths"]) > 5:
            print(f"     … mais {len(item['paths']) - 5}")
        for recusado in item["recusados"]:
            print(f"     ! recusado: {recusado}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
