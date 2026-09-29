# Headroom — Guias de execução

Dois modos de uso, com propósitos diferentes.

| Guia | Quando usar |
|---|---|
| **[01 — Standalone](01-standalone.md)** | Validar a instalação, medir compressão, comprimir arquivos avulsos, usar o proxy com qualquer cliente. **Não precisa de projeto, agente ou esteira.** |
| **[02 — Esteira + GitHub CLI](02-esteira-github-cli.md)** | Rodar a esteira de agentes com 100% das requisições passando pela compressão antes do Foundry. |

Comece pelo **01** — o passo 2 dele (instalação) é pré-requisito dos dois.

---

## Decisão rápida

```
Preciso que os AGENTES rodem comprimidos?
├─ Não → 01-standalone.md
│         proxy avulso + CLI (compress/decode/slice/stats)
└─ Sim → 02-esteira-github-cli.md
          proxy + copilot-cli-headroom.bat + métricas por agente
```

Os dois modos usam o **mesmo proxy na porta 8787**. A diferença é quem aponta
para ele e se as métricas são atribuídas a um agente.

---

## Duas camadas de medição

Elas não se substituem — cada uma sabe o que a outra não sabe.

| Camada | Cobertura | Sabe | Não sabe | Onde |
|---|---|---|---|---|
| **Proxy** | 100% das requisições | model, tokens_before/after, latency_ms | qual agente originou | `~/.headroom/logs/proxy.log` + `.headroom/proxy-requests.jsonl` |
| **Auto-reporte do agente** | só agentes instrumentados | agent_id, phase, run_id | chamadas fora dos agentes | `projects/{p}/outputs/observability/headroom-metrics.jsonl` |

O proxy é cego a quem chamou; o agente é cego ao que passou fora dele.

---

## Referências

- [README da tool](../README.md) — arquitetura, formatos, troubleshooting completo
- [specs/031 — spec](../../../../../specs/031-headroom-context-compression-proxy/spec.md) — especificação
- [specs/031 — quickstart](../../../../../specs/031-headroom-context-compression-proxy/quickstart.md) — verificação em 10 passos
- [specs/031 — research](../../../../../specs/031-headroom-context-compression-proxy/research.md) — superfície real da CLI e formato de compressão
