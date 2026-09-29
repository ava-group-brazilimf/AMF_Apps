# Executando Contêineres Podman no Windows

> **Propósito:** Guia passo a passo para instalar o Podman no Windows e iniciar todos os contêineres gerados pela fase DevOps da pipeline AVA.
> **Público-alvo:** Desenvolvedores, engenheiros de QA e revisores que precisam executar a solução gerada localmente no Windows.
> **Escopo:** Instalação do Podman via `winget`, configuração do Podman Machine e inicialização de todos os arquivos compose produzidos pelo agente de containerização.

---

## Sumário

1. [Pré-requisitos](#pré-requisitos)
2. [Instalando o Podman via Winget](#instalando-o-podman-via-winget)
3. [Iniciando o Podman Machine](#iniciando-o-podman-machine)
4. [Verificando a Instalação](#verificando-a-instalação)
5. [Executando os Contêineres Gerados](#executando-os-contêineres-gerados)
   - [5.1. Ambiente de Desenvolvimento](#51-ambiente-de-desenvolvimento)
   - [5.2. Stack Completa (Microsserviços + Infraestrutura)](#52-stack-completa-microsserviços--infraestrutura)
   - [5.3. Ambiente de Staging](#53-ambiente-de-staging)
   - [5.4. Ambiente de Produção](#54-ambiente-de-produção)
6. [Variáveis de Ambiente (`.env`)](#variáveis-de-ambiente-env)
7. [Solução de Problemas Comuns](#solução-de-problemas-comuns)
8. [Referência de Comandos Úteis](#referência-de-comandos-úteis)

---

## Pré-requisitos

| Requisito | Versão Mínima | Observações |
|-----------|---------------|------------|
| Windows 10/11 | 64-bit, versão 2004+ | WSL2 obrigatório |
| WSL2 | Instalado | `wsl --install` (veja abaixo) |
| Virtualização | Habilitada no BIOS/UEFI | Hyper-V ou backend WSL2 |
| RAM | 8 GB mínimo (16 GB recomendado) | SQL Server + backend + frontend |
| Espaço em Disco | 20 GB livres | Imagens + volumes |

### Habilitar o WSL2 (se ainda não estiver instalado)

Abra o PowerShell **como Administrador** e execute:

```powershell
wsl --install
```

Isso instala o WSL2 com o Ubuntu como distribuição padrão. Após a instalação, **reinicie o computador**.

Para verificar se o WSL2 está em execução:

```powershell
wsl --list --verbose
```

Saída esperada:

```
  NOME          ESTADO          VERSÃO
* ubuntu        Em execução     2
```

---

## Instalando o Podman via Winget

O `winget` (Gerenciador de Pacotes do Windows) vem pré-instalado no Windows 11 e está disponível no [Microsoft Store](https://apps.microsoft.com/detail/9N0DX20HK701) para Windows 10.

### Passo 1 — Atualizar o winget

```powershell
winget upgrade --all
```

### Passo 2 — Instalar o Podman

```powershell
winget install RedHat.Podman
```

Isso instala:
- CLI do **podman**
- Auxiliares do **podman-machine** (backend WSL2)
- **podman-desktop** (GUI opcional — não necessário para uso via CLI)

### Passo 3 — Verificar a Instalação

```powershell
podman --version
```

Saída esperada:

```
podman versão X.Y.Z
```

---

## Iniciando o Podman Machine

No Windows, o Podman executa contêineres dentro de uma máquina virtual WSL2 leve chamada **Podman Machine**.

### Passo 1 — Inicializar a Máquina

```powershell
podman machine init
```

Isso cria uma VM WSL2 com:
- 10 GB de disco (padrão)
- 2 vCPUs (padrão)
- Red Hat Universal Base Image (UBI)

Para personalizar os recursos:

```powershell
podman machine init --disk-size 50 --memory 8192 --cpus 4
```

### Passo 2 — Iniciar a Máquina

```powershell
podman machine start
```

Isso inicializa a VM WSL2. A primeira inicialização pode levar 1–2 minutos.

### Passo 3 — Verificar se a Máquina está em Execução

```powershell
podman machine info
```

Procure por `"running": true` na saída.

### Passo 4 — Configurar Variáveis de Ambiente

O Podman fornece um auxiliar para configurar seu shell:

```powershell
& "C:\Program Files\Red Hat\Podman\podman.exe" machine start --env
```

Ou configure manualmente na sua sessão atual do PowerShell:

```powershell
$env:DOCKER_HOST = "npipe://${Env:USERPROFILE}\.podman\podman.sock"
```

Para tornar isso persistente, adicione a linha ao seu `$PROFILE`:

```powershell
echo '$env:DOCKER_HOST = "npipe://\${Env:USERPROFILE}\.podman\podman.sock"' | Out-File -Append $PROFILE
```

---

## Verificando a Instalação

Execute um contêiner de teste:

```powershell
podman run --rm hello-world
```

Saída esperada:

```
Hello from Podman!
```

Verificar contêineres em execução (deve estar vazio):

```powershell
podman ps
```

Listar todas as imagens:

```powershell
podman images
```

---

## Executando os Contêineres Gerados

O agente `ava-devops-containerize` gera os seguintes arquivos compose dentro do seu projeto:

| Arquivo | Finalidade | Serviços |
|---------|------------|----------|
| `docker-compose.yml` | Desenvolvimento | backend, frontend |
| `docker-compose.full.yml` | Dev local completo (microsserviços) | sqlserver, redis, todos os serviços backend |
| `docker-compose.staging.yml` | Validação de staging | backend (2 réplicas), frontend (2 réplicas) |
| `docker-compose.prod.yml` | Modelo de produção | backend (3 réplicas), frontend (3 réplicas) |

> **Nota:** O Podman é totalmente compatível com arquivos Docker Compose. Use `podman compose` (integrado) em vez de `docker compose`.

Primeiro, navegue até o diretório de código-fonte do projeto gerado. Esse diretório contém os arquivos `docker-compose.yml`, `Dockerfile` e demais artefatos de containerização:

```powershell
cd <caminho/para/o/projeto/outputs/tobe/source-code>
```

### 5.1. Ambiente de Desenvolvimento

A configuração padrão de desenvolvimento com um único serviço de backend e frontend.

```powershell
podman compose -f docker-compose.yml up --build
```

Explicação das flags:
- `-f docker-compose.yml` — especifica o arquivo compose
- `up` — cria e inicia os contêineres
- `--build` — constrói as imagens a partir dos Dockerfiles antes de iniciar

Para executar em modo detached (background):

```powershell
podman compose -f docker-compose.yml up --build -d
```

Acesse os serviços:
- **Frontend:** http://localhost:4200
- **Backend:** http://localhost:8080
- **Health check:** http://localhost:8080/health

Para parar:

```powershell
podman compose -f docker-compose.yml down
```

### 5.2. Stack Completa (Microsserviços + Infraestrutura)

Para projetos com múltiplos serviços — inclui SQL Server, Redis e todos os contextos delimitados do backend.

```powershell
podman compose -f docker-compose.full.yml up --build
```

Isso inicia:
| Serviço | Nome do Contêiner | Porta | Descrição |
|---------|-------------------|-------|-----------|
| `sqlserver` | `<prefixo>-sql` | 1433 | Microsoft SQL Server 2022 |
| `redis` | `<prefixo>-redis` | 6379 | Cache Redis com autenticação |
| `<serviço>` | `<prefixo>-<serviço>` | 5001+ | Cada contexto delimitado do backend |

> **Importante:** O SQL Server leva ~30 segundos para ficar saudável. Os serviços do backend aguardam `service_healthy` antes de iniciar. Tenha paciência.

Para parar e remover todos os dados:

```powershell
podman compose -f docker-compose.full.yml down -v
```

A flag `-v` remove os volumes nomeados (incluindo o banco de dados do SQL Server).

### 5.3. Ambiente de Staging

O staging usa imagens pré-construídas (sem build local) com múltiplas réplicas.

```powershell
podman compose -f docker-compose.staging.yml up -d
```

> **Nota:** O staging espera que as imagens estejam disponíveis em um ACR (`${ACR_LOGIN_SERVER}`). Para testes locais, modifique os campos `image:` no `docker-compose.staging.yml` para usar `build:`, ou construa e envie as imagens primeiro.

Para parar:

```powershell
podman compose -f docker-compose.staging.yml down
```

### 5.4. Ambiente de Produção

O arquivo compose de produção é um **modelo** — não se destina a comandos manuais `up`. Ele é consumido pela pipeline de CI/CD para implantação no Azure Container Apps ou AKS.

Para validação local das configurações de produção:

```powershell
podman compose -f docker-compose.prod.yml config
```

Isso valida a configuração sem iniciar nada.

---

## Variáveis de Ambiente (`.env`)

Todos os arquivos compose carregam segredos de um arquivo `.env`. **Nunca envie `.env` para o git.**

### Passo 1 — Criar o arquivo `.env`

Copie o arquivo de exemplo (gerado junto com os arquivos compose):

```powershell
copy .env.example .env
```

Ou crie manualmente com os valores adequados ao seu ambiente:

```powershell
@echo off
set "SQL_SA_PASSWORD=SuaSenhaForteAqui!"
set "REDIS_PASSWORD=SuaSenhaRedisAqui!"
set "SQL_CONNECTION_STRING=Server=localhost,1433;Database=NomeDoBanco;User Id=sa;Password=SuaSenhaForteAqui!;TrustServerCertificate=true;"
set "REDIS_CONNECTION_STRING=localhost,6379,password=SuaSenhaRedisAqui!"
set "AZURE_AD_CLIENT_ID=seu-client-id-do-azure-ad"
set "APPINSIGHTS_CONNECTION_STRING=sua-string-de-conexao-do-app-insights"
set "APPLICATIONINSIGHTS_CONNECTION_STRING=sua-string-de-conexao-do-app-insights"
set "IMAGE_TAG=local"
set "ACR_LOGIN_SERVER=seu-registry.azurecr.io"
```

### Passo 2 — Variáveis Obrigatórias

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `SQL_SA_PASSWORD` | Senha da conta SA do SQL Server | `YourStrong!Passw0rd` |
| `REDIS_PASSWORD` | Senha de autenticação do Redis | `RedisStrong!Passw0rd` |
| `SQL_CONNECTION_STRING` | Conexão do backend com o SQL Server | `Server=localhost,1433;Database=MeuBd;...` |
| `REDIS_CONNECTION_STRING` | Conexão do backend com o Redis | `localhost,6379,password=...` |
| `AZURE_AD_CLIENT_ID` | Client ID do aplicativo Azure AD | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `APPINSIGHTS_CONNECTION_STRING` | Conexão do Application Insights | `InstrumentationKey=...;Endpoint=...` |
| `IMAGE_TAG` | Tag da imagem Docker | `local`, `dev`, `feature-123` |
| `ACR_LOGIN_SERVER` | URL do Azure Container Registry | `meuregistry.azurecr.io` |

### Passo 3 — Verificar se o `.env` foi Carregado

```powershell
podman compose -f docker-compose.yml config
```

Verifique se as variáveis de ambiente foram resolvidas (não deve haver literais `${VAR}` na saída).

---

## Solução de Problemas Comuns

### Podman Machine Falha ao Iniciar

**Sintoma:** `podman machine start` trava ou gera erros.

**Solução:**
```powershell
podman machine stop
podman machine rm
podman machine init
podman machine start
```

### Porta Já em Uso

**Sintoma:** `bind: address already in use`

**Solução:** Identifique e pare o processo conflitante:

```powershell
# Descobrir o que está usando a porta 8080
netstat -ano | findstr :8080

# Parar o processo (substitua o PID)
Stop-Process -Id <PID> -Force
```

Ou altere o mapeamento de porta no `docker-compose.yml`:

```yaml
ports:
  - "8081:8080"   # host:contêiner
```

### Healthcheck do SQL Server Nunca é Aprovado

**Sintoma:** Serviços do backend nunca iniciam; contêiner do SQL Server está em execução, mas a saúde está `starting`.

**Solução:**
1. Certifique-se de que **ambas** `MSSQL_SA_PASSWORD` e `SQL_SA_PASSWORD` estão definidas com o mesmo valor no `.env`.
2. Aguarde pelo menos 60 segundos — o SQL Server precisa de tempo para inicializar.
3. Verifique os logs:
   ```powershell
   podman compose -f docker-compose.full.yml logs sqlserver
   ```

### WSL2 Sem Espaço em Disco

**Sintoma:** `no space left on device`

**Solução:** Redimensione a máquina Podman:

```powershell
podman machine stop
podman machine set --disk-size 100
podman machine start
```

### WSL2 Sem Memória

**Sintoma:** Contêineres são encerrados inesperadamente; erros OOM nos logs.

**Solução:** Limite o uso de memória do WSL2 globalmente. Crie ou edite `%USERPROFILE%\.wslconfig`:

```ini
[wsl2]
memory=12GB
swap=4GB
localhostForwarding=true
```

Em seguida, reinicie o WSL2:

```powershell
wsl --shutdown
podman machine start
```

### Imagens Não Estão Sendo Construídas (Falhas no Build)

**Sintoma:** `podman compose up --build` falha durante a construção do Dockerfile.

**Solução:**
1. Verifique os logs do build:
   ```powershell
   podman compose -f docker-compose.yml build backend
   ```
2. Certifique-se de que os arquivos `.dockerignore` estão presentes em `backend/` e `frontend/`.
3. Para falhas de build do .NET, verifique se a versão do SDK corresponde ao Dockerfile:
   ```powershell
   dotnet --version
   ```

### Comando Podman Compose Não Encontrado

**Sintoma:** `'podman compose' não é reconhecido como um comando`

**Solução:** O podman compose é integrado desde o Podman 4.x. Se estiver faltando:

```powershell
winget upgrade RedHat.Podman
```

Ou use o plugin standalone:

```powershell
winget install Docker.Compose
```

Em seguida, use `podman-compose` (hífen) em vez de `podman compose` (espaço).

### Permissão Negada no Socket

**Sintoma:** `permission denied while trying to connect to the Podman socket`

**Solução:** Verifique se a variável de ambiente está definida:

```powershell
$env:DOCKER_HOST
# Deve retornar: npipe://\${Env:USERPROFILE}\.podman\podman.sock
```

Adicione ao `$PROFILE` se estiver faltando (veja [Configurar Variáveis de Ambiente](#passo-4-configurar-variáveis-de-ambiente) acima).

---

## Referência de Comandos Úteis

### Gerenciamento de Contêineres

```powershell
# Listar contêineres em execução
podman ps

# Listar todos os contêineres (incluindo parados)
podman ps -a

# Visualizar logs do contêiner (substitua <servico> pelo nome do serviço)
podman compose -f docker-compose.yml logs -f <servico>

# Visualizar as últimas 100 linhas dos logs
podman compose -f docker-compose.yml logs --tail 100 <servico>

# Executar um shell dentro de um contêiner em execução
podman compose -f docker-compose.yml exec <servico> sh

# Reiniciar um serviço específico
podman compose -f docker-compose.yml restart <servico>

# Parar todos os serviços
podman compose -f docker-compose.yml down

# Parar e remover contêineres, redes e volumes
podman compose -f docker-compose.yml down -v

# Remover todas as imagens não utilizadas
podman image prune -a
```

### Gerenciamento de Imagens

```powershell
# Listar imagens
podman images

# Construir uma única imagem
podman build -t meu-backend:local ./backend

# Baixar uma imagem
podman pull mcr.microsoft.com/dotnet/aspnet:10.0

# Remover uma imagem
podman rmi meu-backend:local
```

### Gerenciamento da Máquina

```powershell
# Listar máquinas
podman machine ls

# Parar uma máquina
podman machine stop

# Iniciar uma máquina
podman machine start

# Remover uma máquina
podman machine rm

# SSH na máquina
podman machine ssh
```

### One-Liner de Inicialização Rápida

Para uma reinicialização completa (parar, remover, reconstruir e iniciar):

```powershell
cd <caminho/para/o/projeto/outputs/tobe/source-code>
podman compose -f docker-compose.yml down -v
podman compose -f docker-compose.yml up --build
```

---

## Apêndice A — Mapeamento de Comandos Docker vs Podman

| Docker | Podman | Observações |
|--------|--------|-------------|
| `docker ps` | `podman ps` | Idêntico |
| `docker build -t tag .` | `podman build -t tag .` | Idêntico |
| `docker run ...` | `podman run ...` | Idêntico |
| `docker compose up --build` | `podman compose up --build` | Idêntico |
| `docker-compose up` | `podman compose up` | Sintaxe v1 vs v2 |
| `docker images` | `podman images` | Idêntico |
| `docker logs -f container` | `podman logs -f container` | Idêntico |
| `docker exec -it container sh` | `podman exec -it container sh` | Idêntico |
| `docker system prune -a` | `podman system prune -a` | Idêntico |

---

## Apêndice B — Mapa de Artefatos Gerados

Os seguintes arquivos são produzidos pelo agente `ava-devops-containerize` e devem existir antes de executar os contêineres:

| Artefato | Caminho | Finalidade |
|----------|---------|------------|
| Dockerfile Backend | `backend/Dockerfile` ou `backend/{Servico}/Dockerfile` | Build .NET multi-estágio |
| `.dockerignore` Backend | `backend/.dockerignore` | Excluir segredos do contexto de build |
| Dockerfile Frontend | `frontend/Dockerfile` | Angular multi-estágio + nginx |
| `.dockerignore` Frontend | `frontend/.dockerignore` | Excluir node_modules, segredos |
| nginx.conf | `frontend/nginx.conf` | Config nginx (porta 8080, proxy API) |
| docker-compose.yml | `docker-compose.yml` | Compose de desenvolvimento |
| docker-compose.full.yml | `docker-compose.full.yml` | Stack completa com SQL Server + Redis |
| docker-compose.staging.yml | `docker-compose.staging.yml` | Staging com réplicas |
| docker-compose.prod.yml | `docker-compose.prod.yml` | Modelo de produção |
| `.env.example` | `.env.example` | Modelo para variáveis de ambiente |

---

*Última atualização: 2026-07-16*
*Gerado para: AVA Fabric Migration Platform — Fase DevOps*
