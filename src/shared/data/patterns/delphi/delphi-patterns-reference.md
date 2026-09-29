---
name: delphi-patterns-reference
description: "Referência de padrões Delphi para few-shot dos agentes de análise"
version: "1.0.0"
used_by: [ava-asis-solution-delphi]
---

# Delphi Patterns Reference

## Pattern 1 — Smart UI (Form-Centric)

### Identificadores no código
```pascal
// Evidência: lógica de negócio em eventos de form
procedure TfrmMatricula.btnSalvarClick(Sender: TObject);
begin
  // Validação inline
  if edtNome.Text = '' then begin
    ShowMessage('Nome obrigatório');
    Exit;
  end;
  // Acesso direto ao banco
  qryMatricula.SQL.Text := 'INSERT INTO matricula VALUES (:nome, :data)';
  qryMatricula.ParamByName('nome').AsString := edtNome.Text;
  qryMatricula.ExecSQL;
  ShowMessage('Salvo com sucesso!');
end;
```

### Classificação
- **Padrão**: Smart UI
- **Risco**: 🔴 Alto
- **Mapeamento .NET**: Extrair para `MatricularAlunoCommand + Handler + Validator`

---

## Pattern 2 — DataModule (Repository Implícito)

### Identificadores no código
```pascal
// DataModule com queries centralizadas
type TdmMatricula = class(TDataModule)
  qryListarAlunos: TADOQuery;
  qrySalvarMatricula: TADOQuery;
  procedure qryListarAlunosBeforeOpen(DataSet: TDataSet);
end;

// Form referencia o DataModule
procedure TfrmAlunos.FormCreate(Sender: TObject);
begin
  dmMatricula.qryListarAlunos.Open;
end;
```

### Classificação
- **Padrão**: DataModule Repository
- **Risco**: 🟡 Médio
- **Mapeamento .NET**: `IMatriculaRepository + MatriculaRepository : EF Core`

---

## Pattern 3 — Business Logic in SP (CRÍTICO)

### Identificadores no código
```sql
-- SP com regra de negócio
CREATE PROCEDURE sp_AprovarMatricula
  @IdAluno INT, @IdCurso INT
AS BEGIN
  DECLARE @CargaHoraria INT
  SELECT @CargaHoraria = carga_horaria FROM curso WHERE id = @IdCurso
  
  -- Regra de negócio: aluno precisa ter 75% de frequência
  IF (SELECT frequencia FROM historico WHERE id_aluno = @IdAluno) < 0.75
    RAISERROR('Frequência insuficiente', 16, 1)
  
  UPDATE matricula SET status = 'APROVADO' WHERE id_aluno = @IdAluno
END
```

### Classificação
- **Padrão**: Business Logic in SP
- **Risco**: 🔴 CRÍTICO
- **Ação**: Sprint de Extração OBRIGATÓRIO antes da migração
- **Mapeamento .NET**: `AprovarMatriculaHandler + AprovarMatriculaRule (Domain)`

---

## Pattern 4 — Two-Tier Direto

### Identificadores no código
```pascal
// SQL inline no form sem DataModule
procedure TfrmRelatorio.GerarRelatorio;
var sSQL: string;
begin
  sSQL := 'SELECT * FROM aluno WHERE status = ''' + cbStatus.Text + '''';
  // SQL injection risk! String concatenation
  qryDados.SQL.Text := sSQL;
  qryDados.Open;
end;
```

### Classificação
- **Padrão**: Two-Tier com SQL Injection Risk
- **Risco**: 🔴 Alto + 🔴 Segurança
- **Mapeamento .NET**: `AlunoQueryHandler + Dapper com parâmetros`

---

## Pattern 5 — Rich Domain (Aproveitável)

### Identificadores no código
```pascal
// Unit com regras de negócio isoladas
type TMatricula = class
private
  FStatus: TStatusMatricula;
  FDataInicio: TDate;
public
  function PodeSerAprovada: Boolean;
  procedure Aprovar;
  procedure Reprovar(const Motivo: string);
  property Status: TStatusMatricula read FStatus;
end;

function TMatricula.PodeSerAprovada: Boolean;
begin
  Result := (FStatus = smAtiva) and (DaysBetween(Now, FDataInicio) >= 30);
end;
```

### Classificação
- **Padrão**: Rich Domain Model (parcial)
- **Risco**: 🟢 Baixo
- **Mapeamento .NET**: `Matricula : Entity + PodeSerAprovada() + Aprovar()` — mapeamento quase 1:1
