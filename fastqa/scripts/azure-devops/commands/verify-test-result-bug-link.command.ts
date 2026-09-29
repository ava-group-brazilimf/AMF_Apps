#!/usr/bin/env node
/**
 * FastQA - Verificar Test Result Details
 * Verifica se a vinculação do bug ao test result foi efetivada
 */

import { config } from '../azure-devops.config';

const ORG_URL = config.orgUrl;
const PAT = config.pat;
const PROJECT = config.project;

async function verifyTestResultBugLink() {
    const testRunId = 26;
    const testResultId = 100000;
    const bugId = 39;
    
    console.log('🔍 ═══════════════════════════════════════════════════════════════');
    console.log('   FastQA — Verificar Vinculação Bug ↔ Test Result');
    console.log('═══════════════════════════════════════════════════════════════\n');
    
    try {
        const auth = Buffer.from(`:${PAT}`).toString('base64');
        
        // 1. Verificar Test Result
        console.log('📋 Verificando Test Result...');
        const resultUrl = `${ORG_URL}/${PROJECT}/_apis/test/runs/${testRunId}/results/${testResultId}?api-version=7.1`;
        
        console.log(`🔍 GET: ${resultUrl}\n`);
        
        const response = await fetch(resultUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Basic ${auth}`,
                'Accept': 'application/json'
            }
        });
        
        if (response.ok) {
            const result = await response.json();
            
            console.log('✅ Test Result Details:');
            console.log(`   Test Result ID: ${result.id}`);
            console.log(`   State:          ${result.state || 'N/A'}`);
            console.log(`   Outcome:        ${result.outcome || 'N/A'}`);
            console.log(`   Failure Type:   ${result.failureType || 'N/A'}`);
            console.log(`   Error Message:  ${result.errorMessage || 'N/A'}`);
            console.log(`   Comment:        ${result.comment || 'N/A'}`);
            
            // Verificar se existe associatedBugs
            if (result.associatedBugs && result.associatedBugs.length > 0) {
                console.log('\n🐛 Bugs Associados:');
                result.associatedBugs.forEach(bug => {
                    console.log(`   - Bug ID: ${bug.id}`);
                });
            } else {
                console.log('\n⚠️  Nenhum bug associado encontrado na propriedade "associatedBugs"');
            }
            
            // Verificar se o bug está referenciado em algum campo
            const hasCommentRef = result.comment && result.comment.includes(`#${bugId}`);
            const hasErrorRef = result.errorMessage && result.errorMessage.includes(`#${bugId}`);
            
            console.log('\n📊 Status da Vinculação:');
            console.log(`   Referência no Comment:     ${hasCommentRef ? '✅ SIM' : '❌ NÃO'}`);
            console.log(`   Referência no Error Msg:   ${hasErrorRef ? '✅ SIM' : '❌ NÃO'}`);
            console.log(`   Bugs Associados (API):     ${result.associatedBugs ? result.associatedBugs.length : 0}`);
            
        } else {
            console.error(`❌ Erro ao buscar Test Result: ${response.status} - ${await response.text()}`);
        }
        
        // 2. Verificar Test Run
        console.log('\n📋 Verificando Test Run...');
        const runUrl = `${ORG_URL}/${PROJECT}/_apis/test/runs/${testRunId}?api-version=7.1`;
        
        const runResponse = await fetch(runUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Basic ${auth}`,
                'Accept': 'application/json'
            }
        });
        
        if (runResponse.ok) {
            const run = await runResponse.json();
            console.log(`✅ Test Run #${run.id}: ${run.name || 'N/A'} (${run.state})`);
        }
        
        // 3. Verificar Bug (contrário)
        console.log('\n🐛 Verificando Bug...');
        
        const bugUrl = `${ORG_URL}/${PROJECT}/_apis/wit/workitems/${bugId}?$expand=relations&api-version=7.1`;
        
        const bugResponse = await fetch(bugUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Basic ${auth}`,
                'Accept': 'application/json'
            }
        });
        
        if (bugResponse.ok) {
            const bug = await bugResponse.json();
            console.log(`✅ Bug #${bug.id}: ${bug.fields['System.Title']}`);
            
            if (bug.relations && bug.relations.length > 0) {
                console.log('\n🔗 Relações do Bug:');
                bug.relations.forEach(rel => {
                    console.log(`   - ${rel.rel}: ${rel.url || rel.name || 'N/A'}`);
                });
            }
        }
        
        console.log('\n═══════════════════════════════════════════════════════════════');
        console.log('🎯 CONCLUSÃO');
        console.log('═══════════════════════════════════════════════════════════════\n');
        
        console.log('🔍 Verifique manualmente no Azure DevOps:');
        console.log(`   1. Test Run: https://dev.azure.com/leandroifarias-hubqa/${PROJECT}/_testManagement/runs?runId=${testRunId}&_a=resultSummary`);
        console.log(`   2. Bug:      https://dev.azure.com/leandroifarias-hubqa/${PROJECT}/_workitems/edit/${bugId}`);
        console.log('\n📋 Procure por:');
        console.log('   - Na aba "Test Results" do Test Run, se o Bug aparece linkado');
        console.log('   - No Bug, na aba "Links" ou "Related Work", se o Test Result aparece');
        
    } catch (error) {
        console.error(`❌ Erro na verificação: ${error.message}`);
        process.exit(1);
    }
}

verifyTestResultBugLink().catch(console.error);