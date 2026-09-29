import { test, expect } from '@playwright/test';
import { writeInReport } from '../suporte/utils';
const enviroment = require('../../config/enviroment.json');
const dataUsers = require('../api/data/users.data.json');

test('[306](API) Users - POST - Criação de usuario com sucesso', async ({ request }, testInfo) => {
    // Request
    const _reponse = await request.post(`${enviroment[testInfo.project.name].url_base}${enviroment[testInfo.project.name].api}/users`, {
        headers : {
            "Content-Type":"application/json",
        },
        params : {
            "name":`${dataUsers.name}`,
            "job":`${dataUsers.job}`,
        }
    });
    // Expect Results
    expect(_reponse.status()).toBe(201);
    expect(_reponse.ok).toBeTruthy();
    writeInReport(_reponse);
});
