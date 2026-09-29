program ava_ast_cli;

{ Wrapper CLI do DelphiAST usado pelo AVA Fabric (src/ast_bridge.py -> load_ast).
  Portável: compila em FPC (modo Delphi) e no Delphi/RAD Studio.
  Uso:  ava_ast_cli <input.pas> [output.xml]   (sem output => XML no stdout) }

{$IFDEF FPC}{$MODE Delphi}{$ENDIF}
{$H+}
{$M 33554432,0,33554432}

uses
  SysUtils, Classes,
  DelphiAST,
  DelphiAST.Classes,
  DelphiAST.Consts,
  DelphiAST.Writer,
  StringPool;

var
  InputFile: string;
  OutputFile: string;
  Tree: TSyntaxNode;
  XmlOutput: string;
  OutStream: TFileStream;
  Bytes: TBytes;

begin
  ExitCode := 0;

  if ParamCount < 1 then
  begin
    WriteLn(StdErr, 'Usage: ava_ast_cli <input.pas> [output.xml]');
    WriteLn(StdErr, '  If output.xml is omitted, writes XML to stdout.');
    ExitCode := 1;
    Exit;
  end;

  InputFile := ParamStr(1);

  if not FileExists(InputFile) then
  begin
    WriteLn(StdErr, 'ERROR: File not found: ', InputFile);
    ExitCode := 2;
    Exit;
  end;

  try
    Tree := TPasSyntaxTreeBuilder.Run(InputFile, False, nil, nil);
    try
      XmlOutput := TSyntaxTreeWriter.ToXML(Tree, True);

      if ParamCount >= 2 then
      begin
        OutputFile := ParamStr(2);
        Bytes := TEncoding.UTF8.GetBytes(XmlOutput);
        OutStream := TFileStream.Create(OutputFile, fmCreate);
        try
          OutStream.WriteBuffer(Bytes[0], Length(Bytes));
        finally
          OutStream.Free;
        end;
        WriteLn(StdErr, 'OK: AST written to ', OutputFile);
      end
      else
        WriteLn(XmlOutput);
    finally
      Tree.Free;
    end;
  except
    on E: Exception do
    begin
      WriteLn(StdErr, 'PARSE_ERROR: ', E.ClassName, ': ', E.Message);
      ExitCode := 3;
    end;
  end;
end.
