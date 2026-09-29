import { expect, type Locator, type Page } from '@playwright/test';

export class NewUserPage {
  readonly register_PageTitle: Locator;

  constructor(page: Page) {
    this.register_PageTitle = page.locator('//h1');
  }

  async checkRegisterPageTitle() {
    await expect(this.register_PageTitle).toHaveText("Register");
  }

}