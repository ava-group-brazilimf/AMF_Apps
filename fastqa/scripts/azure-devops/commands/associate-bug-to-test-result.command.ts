#!/usr/bin/env node
/**
 * FastQA - Associate Bug to Test Result (Real Azure DevOps Link)
 * Cria vinculação real entre bug e test result usando a API específica
 */

import { config } from '../azure-devops.config';

const ORG_URL = config.orgUrl;
const PAT = config.pat;
const PROJECT = config.project;

async function associateBugToTestResult() {
    const bugId = 39;
    const testRunId = 26;
    const testResultId = 100000;
    
    console.log('🔗 ═══════════════════════════════════════════════════════════════');
    console.log('   FastQA — Associar Bug ao Test Result (Vinculação Real)');
    console.log('═══════════════════════════════════════════════════════════════\n');
    
    console.log(`📋 Parâmetros:`);
    console.log(`   Bug ID:         #${bugId}`);
    console.log(`   Test Run ID:    #${testRunId}`);
    console.log(`   Test Result ID: #${testResultId}`);
    console.log(`   Project:        ${PROJECT}\n`);
    
    try {
        // 1. Primeira abordagem: Associar bug ao Test Result
        console.log('🔧 Associando bug ao Test Result...');
        
        const auth = Buffer.from(`:${PAT}`).toString('base64');
        
        // Payload para associar bug ao test result
        const associatePayload = [
            {
                id: testResultId,
                associatedBugs: [
                    {
                        id: bugId,
                        type: "Bug"
                    }
                ]
            }
        ];
        
        const associateUrl = `${ORG_URL}/${PROJECT}/_apis/test/runs/${testRunId}/results?api-version=7.1-preview.6`;
        
        console.log(`🔍 PATCH: ${associateUrl}`);
        
        const response = await fetch(associateUrl, {
            method: 'PATCH',
            headers: {
                'Authorization': `Basic ${auth}`,
                'Content-Type': 'application/json-patch+json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(associatePayload)
        });
        
        if (response.ok) {
            const result = await response.json();
            console.log('✅ Bug associado ao Test Result com sucesso!');
            console.log(`📊 Response: ${result.count || 0} item(s) atualizado(s)`);
        } else {
            const errorText = await response.text();
            console.log(`⚠️  Primeira tentativa falhou: ${response.status} - ${errorText}`);
            
            // 2. Segunda abordagem: Atualizar Test Result com bug information
            console.log('\n🔧 Tentativa alternativa: Atualizando Test Result...');
            
            const updatePayload = [
                {
                    id: testResultId,
                    failureType: "Known Issue",
                    comment: `🐛 Bug #${bugId} associado a esta falha | Ver: https://dev.azure.com/leandroifarias-hubqa/${PROJECT}/_workitems/edit/${bugId}`,
                    outcome: "Failed",
                    errorMessage: `Bug #${bugId}: [BUG] Falha na validação do formulário de login - TC-15`
                }
            ];
            
            const updateResponse = await fetch(associateUrl, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Basic ${auth}`,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(updatePayload)
            });
            
            if (updateResponse.ok) {
                console.log('✅ Test Result atualizado com informações do bug!');
            } else {
                const updateError = await updateResponse.text();
                console.log(`❌ Atualização alternativa também falhou: ${updateResponse.status} - ${updateError}`);
            }
        }
        
        // 3. Terceira abordagem: Criar Test Result Bug (API específica)
        console.log('\n🔧 Criando associação via Test Result Bug API...');
        
        const bugAssocUrl = `${ORG_URL}/${PROJECT}/_apis/test/runs/${testRunId}/results/${testResultId}/bugs?api-version=7.1-preview.1`;
        
        const bugPayload = {
            "bugId": bugId
        };
        
        console.log(`🔍 POST: ${bugAssocUrl}`);
        
        const bugResponse = await fetch(bugAssocUrl, {
            method: 'POST',
            headers: {
                'Authorization': `Basic ${auth}`,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(bugPayload)
        });
        
        if (bugResponse.ok) {
            console.log('✅ Associação via Test Result Bug API criada!');
        } else {
            const bugError = await bugResponse.text();
            console.log(`⚠️  Test Result Bug API: ${bugResponse.status} - ${bugError}`);
        }
        
        console.log('\n═══════════════════════════════════════════════════════════════');
        console.log('📊 RESULTADO FINAL');
        console.log('═══════════════════════════════════════════════════════════════\n');
        
        console.log(`🔗 Verifique a vinculação nos links:`);
        console.log(`   Bug #${bugId}:        https://dev.azure.com/leandroifarias-hubqa/${PROJECT}/_workitems/edit/${bugId}`);
        console.log(`   Test Run #${testRunId}: https://dev.azure.com/leandroifarias-hubqa/${PROJECT}/_testManagement/runs?runId=${testRunId}&_a=resultSummary`);
        console.log(`   Test Result:      Dentro do Test Run, procure por Result ID ${testResultId}`);
        
    } catch (error) {
        console.error(`❌ Erro na associação: ${error.message}`);
        process.exit(1);
    }
}

associateBugToTestResult().catch(console.error);