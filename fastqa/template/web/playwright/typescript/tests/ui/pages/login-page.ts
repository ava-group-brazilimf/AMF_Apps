import { expect, type Locator, type Page } from '@playwright/test';

export class LoginPage {
  readonly login_Page: Page;
  readonly username_TextBox: Locator;
  readonly password_TextBox: Locator;
  readonly login_Button: Locator;
  readonly newUser_Button: Locator;
  readonly loginError_Msg: Locator;

  constructor(page: Page) {
    this.login_Page = page;
    this.username_TextBox = page.locator('//*[@id="userName"]');
    this.password_TextBox = page.locator('#password');
    this.login_Button = page.locator('button', { hasText: 'Login' });
    this.newUser_Button = page.locator('#newUser');
    this.loginError_Msg = page.locator('#name');
  }

  async goto(url) {
    await this.login_Page.goto(url);
  }

  async login(user, pass) {
    await this.username_TextBox.fill(user)
    await this.password_TextBox.fill(pass)
    await this.login_Button.click();
  }

  async accessNewUserPage() {
    await this.newUser_Button.click();
  }

  async checkLoginErrorMsg(msg) {
    await expect(this.loginError_Msg).toContainText(msg);
  }

}