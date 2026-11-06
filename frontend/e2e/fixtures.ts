import { test as base, expect, Page } from '@playwright/test';

export interface TestUser {
  username: string;
  email: string;
  password: string;
}

export interface MonitoredPage {
  page: Page;
  consoleErrors: string[];
  pageErrors: string[];
  failedRequests: string[];
}

export const test = base.extend<{
  monitoredPage: MonitoredPage;
  testUser: TestUser;
  secondUser: TestUser;
}>({
  testUser: async ({ request }, use) => {
    const id = Math.floor(Math.random() * 1000000);
    const user: TestUser = {
      username: `pw_user_${id}`,
      email: `pw_user_${id}@example.com`,
      password: `Password123!${id}`
    };
    await request.post('http://127.0.0.1:8000/api/v1/auth/register', {
      data: {
        username: user.username,
        email: user.email,
        password: user.password,
        full_name: `Engineer ${id}`
      }
    });
    await use(user);
  },

  secondUser: async ({ request }, use) => {
    const id = Math.floor(Math.random() * 1000000);
    const user: TestUser = {
      username: `pw_user_sec_${id}`,
      email: `pw_user_sec_${id}@example.com`,
      password: `Password123!${id}`
    };
    await request.post('http://127.0.0.1:8000/api/v1/auth/register', {
      data: {
        username: user.username,
        email: user.email,
        password: user.password,
        full_name: `Sec Engineer ${id}`
      }
    });
    await use(user);
  },

  monitoredPage: async ({ page }, use) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    const failedRequests: string[] = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        const txt = msg.text();
        // Ignore expected favicon 404, vite hmr noise, or initial unauthenticated /auth/me 401 probe
        if (
          !txt.includes('favicon.ico') &&
          !txt.includes('vite') &&
          !txt.includes('401 (Unauthorized)')
        ) {
          consoleErrors.push(txt);
        }
      }
    });

    page.on('pageerror', err => {
      pageErrors.push(err.message);
    });

    page.on('response', resp => {
      const url = resp.url();
      const status = resp.status();
      if (
        status >= 500 ||
        (status >= 400 &&
          !url.includes('/auth/login') &&
          !url.includes('/auth/register') &&
          !url.includes('/auth/me') &&
          !url.includes('/submissions/upload') &&
          !url.includes('/analysis') &&
          !url.includes('/clarifications') &&
          !url.includes('/prd') &&
          !url.includes('/validation'))
      ) {
        failedRequests.push(`${status} ${resp.request().method()} ${url}`);
      }
    });

    await use({ page, consoleErrors, pageErrors, failedRequests });
  }
});

export { expect };

