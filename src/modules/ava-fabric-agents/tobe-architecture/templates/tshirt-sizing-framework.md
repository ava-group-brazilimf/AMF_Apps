---
template_id: tshirt-sizing-framework
agent: ava-tobe-migration-plan
version: "1.0.0"
description: "Exemplos concretos de classificação T-Shirt (XS→XL), guia de casos-limite, propriedades derivadas e schema obrigatório de tshirt-sizing-rationale.md"
---

# T-Shirt Sizing Framework — Reference Specification

> **Load when**: executing Steps 2-4 of the Execution Protocol.
> **Core rule (also inline in agent)**: `T-shirt = max(T-shirt_FP, T-shirt_Integrações, T-shirt_Endpoints, T-shirt_Entidades, T-shirt_Regras)`.

---

## Exemplos Concretos de Classificação

> Todos os exemplos usam nomes genéricos (Módulo A, Serviço B). A lógica é project-agnostic — aplica-se a qualquer BC independentemente do domínio de negócio.

### T-Shirt XS — Módulo isolado, sem integrações

| Dimensão | Valor medido | Faixa XS | Classificação |
|---|---|---|---|
| Function Points | 4 | ≤ 5 | XS |
| Integrações externas | 0 | 0 – 1 | XS |
| Endpoints REST/SOAP | 5 | ≤ 5 | XS |
| Entidades BD | 3 | ≤ 3 | XS |
| Regras de negócio | 4 | ≤ 5 | XS |

> **T-Shirt = XS** · Dimensão determinante: todas iguais (XS) · Caso típico: módulo utilitário ou de suporte sem dependências.

---

### T-Shirt S — Módulo simples com 1–2 integrações

| Dimensão | Valor medido | Faixa | Classificação |
|---|---|---|---|
| Function Points | 11 | 6 – 15 | S |
| Integrações externas | 2 | 1 – 2 | S |
| Endpoints REST/SOAP | 13 | 6 – 15 | S |
| Entidades BD | 7 | 4 – 10 | S |
| Regras de negócio | 9 | 6 – 15 | S |

> **T-Shirt = S** · Dimensão determinante: todas iguais (S) · Caso típico: serviço CRUD simples com autenticação e 1–2 dependências externas.

---

### T-Shirt M — Endpoints ou entidades empurram para cima

| Dimensão | Valor medido | Faixa | Classificação |
|---|---|---|---|
| Function Points | 10 | 6 – 15 | **S** |
| Integrações externas | 3 | 3 – 4 | **M** ← determinante |
| Endpoints REST/SOAP | 14 | 6 – 15 | **S** |
| Entidades BD | 12 | 11 – 20 | **M** |
| Regras de negócio | 14 | 6 – 15 | **S** |

> **T-Shirt = M** · Dimensão determinante: Integrações externas (valor 3 → faixa M) · Caso-limite: FP e Endpoints seriam S, mas as integrações puxam para M.

---

### T-Shirt L — Entidades BD ou regras de negócio dominam

| Dimensão | Valor medido | Faixa | Classificação |
|---|---|---|---|
| Function Points | 20 | 16 – 30 | **M** |
| Integrações externas | 6 | 5 – 7 | **L** ← determinante |
| Endpoints REST/SOAP | 15 | 6 – 15 | **S** |
| Entidades BD | 25 | 21 – 40 | **L** |
| Regras de negócio | 35 | 31 – 50 | **L** |

> **T-Shirt = L** · Dimensão determinante: Integrações externas (valor 6 → faixa L) · Caso-limite: Endpoints são S, mas integrações, entidades e regras convergem para L.

---

### T-Shirt XL — Módulo central com alto acoplamento

| Dimensão | Valor medido | Faixa | Classificação |
|---|---|---|---|
| Function Points | 80 | > 60 | **XL** ← determinante |
| Integrações externas | 8 | > 7 | **XL** |
| Endpoints REST/SOAP | 70 | > 60 | **XL** |
| Entidades BD | 45 | > 40 | **XL** |
| Regras de negócio | 55 | > 50 | **XL** |

> **T-Shirt = XL** · Dimensão determinante: FP (valor 80, todas as dimensões convergem para XL) · Caso típico: módulo core com alto acoplamento, candidato a Strangler Fig incremental.

---

### Guia de casos-limite (quando o T-shirt está na fronteira)

| Situação | Regra de desempate |
|---|---|
| 2 dimensões em M, 3 em S | T-shirt = M (max ganha) |
| 1 dimensão em L, demais em S | T-shirt = L (1 dimensão basta para elevar) |
| Dimensão com valor `?` (dado ausente) | Registrar como `INCOMPLETE` — NÃO inferir; escalar para levantamento antes de sequenciar a wave |
| Módulo com 0 integrações mas FP alto | Classificar pelo FP; observar na gap-list que o módulo é standalone |

---

## Propriedades por T-Shirt (derivadas — não são critérios de sizing)

| T-Shirt | Cobertura IA estimada | Máx. módulos por wave |
|---|---|---|
| XS | ~ 90 % | 4 |
| S | ~ 75 % | 3 |
| M | ~ 55 % | 2 |
| L | ~ 35 % | 2 |
| XL | ~ 15 % | 1 |

> A cobertura de IA é uma **consequência** do T-shirt, não um critério de determinação. Usá-la apenas para comunicar ao time de remediação a carga de trabalho manual esperada.

---

## Schema obrigatório — `tshirt-sizing-rationale.md`

| BC / Módulo | FP | Integrações | Endpoints | Entidades BD | Regras de Negócio | T-Shirt | Dimensão determinante | Justificativa |
|---|---|---|---|---|---|---|---|---|
| [BC Name] | XS/S/M/L/XL | XS/S/M/L/XL | XS/S/M/L/XL | XS/S/M/L/XL | XS/S/M/L/XL | **[maior]** | [qual dimensão] | [por quê foi determinante] |

> Todas as 5 colunas dimensionais são OBRIGATÓRIAS. Usar `?` apenas se o dado não estiver disponível em nenhum artefato AS-IS — nunca omitir a coluna.
