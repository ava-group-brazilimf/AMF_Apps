# Typescript-Automated-Tests UI-API
  
Este projeto é um setup de testes automatizados escrita em TypeScript, utilizando o Playwright para testes de interface de usuário e testes de API.  
  
## Recursos  
  
- Automatização de testes de interface de usuário (UI).  
- Automatização de testes de API.  
- Relatórios de testes com o `monocart-reporter`.  
- Suporte para diferentes ambientes de testes como desenvolvimento (DEV) e homologação (HML).  
  
## Pré-requisitos  
  
Antes de começar, você precisará ter o Node.js e o npm instalados em sua máquina. Para verificar se você já tem o Node.js e o npm instalados, você pode executar:  
  
```bash  
node --version  
npm --version  
```
Caso não estejam instalados, você pode baixá-los e instalá-los a partir do site oficial do Node.js.

## Instalação
 
Para instalar as dependências do projeto, clone o repositório e execute o seguinte comando:

```bash 
git clone https://O2M-QA@dev.azure.com/O2M-QA/Technical-Patterns/_git/Web-API-TypeScript-Plawright
cd typescript-automated-tests  
npm install
```

## Uso
 
Para executar os testes, você pode utilizar os seguintes comandos:
```bash 
npm run test # Executa todos os testes.  
npm run reporter # Exibe o relatório dos testes.  
npm run ui # Executa os testes com uma interface de usuário.  
npm run dev # Executa os testes para a massa de dados de desenvolvimento (DEV).  
npm run hml # Executa os testes para a massa de dados de homologação (HML).  
```