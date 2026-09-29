import { test } from '@playwright/test';
import { LoginPage } from './pages/login-page';
import { NewUserPage } from './pages/new-user-page';
const enviroment = require('../../config/enviroment.json');

// test('[305](UI) Login - Realizar Login Com Insucesso', async ({ page }, testInfo) => {
//     const loginPage = new LoginPage(page);
//     await loginPage.goto(`${enviroment[testInfo.project.name].url_ui}`);
//     await loginPage.login('demo', '123');
//     await loginPage.checkLoginErrorMsg('Invalid username or password!');
// });

test('(UI) Login - Acessar a opcao New User', async ({ page }, testInfo) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto(`${enviroment[testInfo.project.name].url_ui}`);

    await loginPage.accessNewUserPage();

    const newUserPage = new NewUserPage(page);
    await newUserPage.checkRegisterPageTitle();
});

 //Data Json provider
const invalidCredentials = require('../ui/data/invalid-credentials.data.json');
for (const invalidCredential of invalidCredentials) {
    test(`(UI) Login - Realizar Login Com Insucesso = Senha ${invalidCredential.password}`, async ({ page }, testInfo) => {
        const loginPage = new LoginPage(page);
        await loginPage.goto(`${enviroment[testInfo.project.name].url_ui}`);

        await loginPage.username_TextBox.fill(invalidCredential.username);
        await loginPage.password_TextBox.fill(invalidCredential.password);
        await loginPage.login_Button.click();

        await loginPage.login(invalidCredential.username, invalidCredential.password);
        await loginPage.checkLoginErrorMsg('Invalid username or password!');
    });
} 
       
/* //Data Csv provider
import fs from 'fs';
import path from 'path';
import { parse } from 'csv-parse/sync';

const invalidCredentialsCSV = parse(fs.readFileSync(path.join(__dirname, 'data', 'invalid-credentials.data.csv')), {
    columns: true,
    skip_empty_lines: true
});

for (const invalidCredentialCSV of invalidCredentialsCSV) {
    test(`[305](UI) Login - Realizar Login Com Insucesso = Senha ${invalidCredentialCSV.password}`, async ({ page }, testInfo) => {
        const loginPage = new LoginPage(page);
        await loginPage.goto(`${enviroment[testInfo.project.name].url_ui}`);
        await loginPage.login(invalidCredentialCSV.username, invalidCredentialCSV.password);
        await loginPage.checkLoginErrorMsg('Invalid username or password!');
    });
}*/