# SQL Strategy — Changelog Corporativo

Bump da versão aqui exige regeneração de `outputs/tobe/db/sql-strategy.md` em todos os projetos na próxima onda TO-BE (ver `database-policy-tobe.md`).

| Versão | Data | Autor | Mudanças |
|---|---|---|---|
| 1.0.0 | 2026-05-13 | Arquitetura Corporativa | Versão inicial: zero SP de domínio, zero triggers, EF Core Migrations exclusivas, views só no Read Side, política de backup/retenção. |
| 1.1.0 | 2026-05-13 | Arquitetura Corporativa | P0/P1: distinção SP de domínio × SP de plataforma; contrato de Outbox + idempotência de projetor + versionamento de eventos; forward-only em PRD; drift detection; online schema change; separação schema/data migration; versionamento de view e SLA de staleness; PITR; validação semanal de backup; crypto-shredding (LGPD); rotação CMK/HSM; matriz de permissões; rede privada; concorrência otimista. |
