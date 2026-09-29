Ready for review
Select text to add comments on the plan
Plano: garantir compressão real do Headroom antes do LLM + atualizar binário Linux
Contexto
O usuário rodou o agente delphi-analyzer.prompt.md (com um "STEP 3" que ele mesmo adicionou, de relatório de evidências Headroom) e o log mostrou 0% de redução em todos os 9 artefatos, todos router:noop — inclusive 05_procedures com 56.376 tokens (82,6% do total). Isso é reproduzível: já tinha visto o mesmo padrão nesta sessão contra examples/Meu-ERP, e o .ava-fabric/compressed/manifest.json real do usuário confirma byte a byte os mesmos números do log colado.

Investiguei a fundo (leitura do código-fonte instalado do pacote headroom-ai==0.30.0 + reprodução direta contra o artefato real) e encontrei a causa raiz, confirmada empiricamente — não é hipótese.

O usuário também pediu para verificar se a tool (ava_ast_cli) está atualizada tanto para Windows quanto Linux — achei que não está: o binário Linux bundled nunca foi recompilado com o fix de recursão infinita que aplicamos ao Windows nesta sessão.

Causa raiz do Headroom sempre dar noop (confirmada empiricamente)
headroom/transforms/content_detector.py::_try_detect_json só reconhece array JSON no nível raiz (content.strip().startswith("[")). Todo artefato deste projeto é um objeto no nível raiz (o envelope de schemas.py::envelope(): {"artifact":..., "payload": {...}, "_volatile":...}). Resultado: cai sempre em ContentType.PLAIN_TEXT, nunca chega no SmartCrusher, o caminho de texto não reduz nada, e o ContentRouter descarta o resultado nulo — daí transforms_applied: ["router:noop"] em 100% dos artefatos, sempre, em qualquer projeto que use esse formato de envelope.

Fator secundário (não é o alvo do fix): no Windows, o Headroom usa por padrão o detector puro-Python (mais fraco) em vez do nativo Rust/Magika, que classificaria certo — mas o próprio Headroom marca esse backend nativo como "unsafe by default no Windows" (risco de deadlock documentado, mitigado por um watchdog interno de 5s). Cogitei usar HEADROOM_DETECT_BACKEND=rust mas descartei em favor do fix abaixo, que não carrega esse risco.

Fix verificado empiricamente (rodei eu mesmo contra .ava-fabric/extraction/05_procedures.json, chamada idêntica à que o projeto já usa): embrulhar o documento inteiro num array de 1 elemento antes de comprimir (json.dumps([doc])) e desembrulhar depois (json.loads(content)[0]). Resultado real: 36.982 → 20.529 tokens (-44,5%), transforms_applied: ['router:smart_crusher:0.05']. Confirmei que o envelope (artifact, payload, _volatile etc.) sobrevive intacto depois de desembrulhar.

Achado adicional importante: o formato do array comprimido pelo SmartCrusher real da Headroom não é {"__headroom__":"factored_array",...} (o formato do fallback local) — é uma STRING compacta tipo CSV:

[650]{kind:string,name:string,params:json,returns:string?,source_ref.file:string,source_ref.line:int,unit:string}
procedure,setIdBanco,"[""pIdBanco : integer""]",,uClassBancos.pas,15,uClassBancos
Isso significa que agents/delphi-analyzer.prompt.md (e a cópia espelhada .github/skills/delphi-analyzer.prompt.md) precisam de instrução de reidratação nova pra esse formato — hoje só documentam o formato do fallback local, porque até agora o Headroom real nunca comprimia nada de verdade.

Implementação
A. Fix em src/headroom_precompress.py
Substituir _compress_with_headroom (linhas 36-53) por:

def _compress_with_headroom(raw: str, model: str) -> dict[str, Any] | None:
    """Comprime via headroom.compress(). Retorna dict de resultado ou None."""
    try:
        from headroom import compress, CompressConfig
    except Exception:
        return None
    try:
        doc = json.loads(raw)
    except Exception:
        return None
    try:
        # Headroom só detecta JSON_ARRAY no nível raiz (content.startswith("[")) —
        # todo artefato aqui é um objeto ({"artifact":..., "payload":...}), então
        # embrulhamos num array de 1 elemento pra acionar o SmartCrusher real, e
        # desembrulhamos depois. Verificado empiricamente: sem isso, 100% dos
        # artefatos caem em PLAIN_TEXT e o router sempre reporta "noop".
        wrapped = json.dumps([doc], ensure_ascii=False)
        cfg = CompressConfig(compress_user_messages=True, protect_recent=0,
                             min_tokens_to_compress=100)
        res = compress([{"role": "user", "content": wrapped}], model=model, config=cfg)
        content = res.messages[-1]["content"]
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        try:
            parsed = json.loads(content)
            if not (isinstance(parsed, list) and len(parsed) == 1):
                return None  # forma inesperada -> cai pro fallback local
            unwrapped = json.dumps(parsed[0], ensure_ascii=False)
        except Exception:
            return None
        return {"content": unwrapped, "tokens_in": res.tokens_before,
                "tokens_out": res.tokens_after,
                "transforms": list(res.transforms_applied), "mode": "headroom"}
    except Exception:
        return None
_compress_fallback (linhas 96-103) não precisa mudar — já opera sobre o objeto Python parseado (doc["payload"]), nunca dependeu do prefixo [.
precompress()/cálculo de reduction_pct (linhas 109-130) não precisa mudar — tokens_in/tokens_out continuam vindo da mesma medição (agora sobre o conteúdo embrulhado), a razão continua consistente.
Não introduzir HEADROOM_DETECT_BACKEND=rust em lugar nenhum — o fix de embrulhar já resolve sem depender do backend "unsafe" no Windows.
Aproveitar a mudança pra corrigir a contagem desatualizada "8 artefatos" nos comentários/docstring deste arquivo (linhas 4 e 135, achado à parte, de passagem — já estava desatualizado desde a sessão anterior).
B. agents/delphi-analyzer.prompt.md e .github/skills/delphi-analyzer.prompt.md
Ambos têm o mesmo texto nas linhas 61-63 (confirmado, byte a byte idêntico nos dois arquivos). Substituir em ambos:

Leia os 9 artefatos comprimidos de `./.ava-fabric/compressed/` (não o código cru).
Se um array vier fatorado (`{"__headroom__":"factored_array","schema":[...],"rows":[...]}`),
reidrate mentalmente: cada `row` é um registro cujas chaves são o `schema`.
por:

Leia os 9 artefatos comprimidos de `./.ava-fabric/compressed/` (não o código cru).
Um array original pode chegar comprimido em uma de duas formas — reidrate mentalmente
antes de interpretar:

- **Marcador local (fallback sem Headroom real)**: um objeto
  `{"__headroom__":"factored_array","schema":[...],"rows":[...]}`. Cada `row` é um
  registro cujas chaves são o `schema`, na mesma ordem.
- **Tabela CCR do Headroom real**: um campo que antes era array JSON vira uma
  **string simples** cujo conteúdo começa com um cabeçalho
  `[<count>]{col1:tipo1,col2:tipo2,...}` seguido de uma linha por registro em CSV.
  Exemplo real:
[650]{kind:string,name:string,params:json,returns:string?,source_ref.file:string,source_ref.line:int,unit:string} procedure,setIdBanco,"[""pIdBanco : integer""]",,uClassBancos.pas,15,uClassBancos

Para reidratar: leia a 1ª linha, extraia `count` e a lista `col:tipo` — essas são
as colunas na ordem em que aparecem em cada linha seguinte (CSV padrão: vírgula
separa campos, campos com vírgula/aspas vêm entre aspas duplas com `""` escapando
aspas internas). Mapeie os valores posicionalmente aos nomes de coluna.
Sem outras mudanças nesses arquivos para este fix (STEP 1, "Contrato de saída" e "Regras de custo" já dizem "use o manifest.json" e continuam corretos).

C. Kit de build Linux (o binário bundled está desatualizado)
bin/ava_ast_cli.exe (Windows) foi recompilado nesta sessão com o fix do bug de recursão infinita (SimpleParser.pas/TStringStreamHelper) + submódulos. bin/ava_ast_cli (Linux, sem extensão) nunca foi recompilado — ainda tem o bug (stack overflow ao parsear praticamente qualquer .pas). Esta máquina não tem WSL nem Docker (confirmado: wsl --status diz não instalado, docker --version não encontrado) — não dá pra recompilar nem verificar o binário Linux nesta sessão. O que dá pra fazer agora: preparar o kit de build pronto pra rodar assim que houver um ambiente Linux/WSL/Docker disponível (própria máquina do usuário, CI, container).

Novo bin/build-linux/build-fpc.sh (tradução 1:1 do bin/build-windows/build-fpc.bat, reaproveitando o mesmo ava_ast_cli.lpr via ../build-windows/ava_ast_cli.lpr — o wrapper já é portável, {$IFDEF FPC}, sem código condicional de plataforma, não precisa de cópia):
#!/usr/bin/env bash
# ============================================================
#  AVA Fabric - Build do ava_ast_cli no Linux via FPC
#  Pre-req: Free Pascal 3.2.2+ (fpc no PATH). Debian/Ubuntu: apt install fp-compiler
#           (nome do pacote varia por distro/versao).
#  Uso:  ./build-fpc.sh     (rode de dentro de bin/build-linux/)
#  Gera: ../ava_ast_cli
# ============================================================
set -euo pipefail
SRC="../../examples/DelphiAST/Source"
LPR="../build-windows/ava_ast_cli.lpr"

if ! command -v fpc >/dev/null 2>&1; then
  echo "[ERRO] fpc nao encontrado no PATH. Instale o Free Pascal (ex.: sudo apt install fp-compiler)."
  exit 1
fi

mkdir -p build

if ! fpc -Mdelphi \
  -Fu"$SRC" \
  -Fu"$SRC/SimpleParser" \
  -Fu"$SRC/FreePascalSupport" \
  -Fu"$SRC/FreePascalSupport/FPC_StringBuilder/Src" \
  -Fu"$SRC/FreePascalSupport/Generics.Collection" \
  -Fi"$SRC/SimpleParser" \
  -FUbuild \
  -FE.. \
  "$LPR"; then
  echo "[ERRO] Falha na compilacao. Se reclamar de Generics.Collections,"
  echo "       remova a linha -Fu .../Generics.Collection (o FPC ja traz a sua)."
  exit 1
fi

echo
echo "[OK] Gerado: ../ava_ast_cli"
chmod +x ../ava_ast_cli
../ava_ast_cli || true
Novo docs/BUILD_LINUX.md, espelhando a estrutura de docs/BUILD_WINDOWS.md (intro + aviso de que o binário bundled está desatualizado, "Caminho A — FPC" com passos 1-3, "3. Verificar o binário" smoke test contra examples/Meu-ERP/Classes/uClassContasCorrente.pas, "4. Ligar na tool", "Notas").
bin/README.md: trocar a seção genérica "Recompilar (outra plataforma...)" por duas subseções irmãs — "Windows (.exe)" (já existe, sem mudança) e nova "Linux (regerar o binário bundled)" apontando pro kit acima + docs/BUILD_LINUX.md, com aviso explícito:
Atenção: o bin/ava_ast_cli incluído está desatualizado — compilado antes da correção do bug de recursão infinita em TStringStreamHelper.GetDataString (SimpleParser.pas). Não use em produção sem recompilar com o kit acima.

Verificação
A (fix Headroom):

python src/run_pipeline.py ./examples/Meu-ERP --extraction ./.ava-fabric/extraction --compressed ./.ava-fabric/compressed
Conferir manifest.json: 05_procedures com reduction_pct na faixa de ~40-45% e transforms tipo ["router:smart_crusher:..."], não mais ["router:noop"]. Artefatos pequenos (abaixo de min_tokens_to_compress=100) podem legitimamente continuar com pouca/nenhuma redução — esperado, não é bug.
Loop de sanidade sobre os 9 arquivos de saída: cada um continua JSON válido com as chaves do envelope (artifact, schema_version, project, payload, _volatile) intactas.
B (prompt.md): sem código pra rodar — validar manualmente que a amostra CCR real capturada ([650]{...} + linha CSV) é reconstruível seguindo a nova instrução (extrair count+colunas do cabeçalho, split CSV respeitando aspas escapadas, mapear posicionalmente).

C (build Linux): não dá pra executar/verificar nesta máquina (sem WSL/Docker) — documentar isso explicitamente. Quando houver ambiente disponível: rodar build-fpc.sh, confirmar bin/ava_ast_cli regerado, e smoke test igual ao que docs/BUILD_WINDOWS.md já usa pro Windows.

Arquivos críticos
src/headroom_precompress.py — fix do wrap/unwrap em _compress_with_headroom.
agents/delphi-analyzer.prompt.md e .github/skills/delphi-analyzer.prompt.md — instrução de reidratação do formato CCR real.
Novo bin/build-linux/build-fpc.sh.
Novo docs/BUILD_LINUX.md.
bin/README.md — nova subseção Linux + aviso de binário desatualizado.