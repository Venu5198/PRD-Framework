import { test, expect } from './fixtures';

test.describe('Scenario H: Security and Authorization Workflows', () => {
  let userAId: string;
  let userBId: string;
  let tokenA: string;
  let tokenB: string;
  let projectAId: string;

  test.beforeEach(async ({ testUser, secondUser, request }) => {
    // Authenticate User A
    const loginARes = await request.post('http://127.0.0.1:8000/api/v1/auth/login', {
      data: { username: testUser.username, password: testUser.password }
    });
    const dataA = await loginARes.json();
    tokenA = dataA.access_token;

    // Authenticate User B
    const loginBRes = await request.post('http://127.0.0.1:8000/api/v1/auth/login', {
      data: { username: secondUser.username, password: secondUser.password }
    });
    const dataB = await loginBRes.json();
    tokenB = dataB.access_token;

    // Create a project for User A
    const projRes = await request.post('http://127.0.0.1:8000/api/v1/projects', {
      headers: { Authorization: `Bearer ${tokenA}` },
      data: {
        title: 'User A Confidential System',
        description: 'Classified architecture documentation',
        target_domain: 'Healthcare & Privacy Systems'
      }
    });
    const proj = await projRes.json();
    projectAId = proj.id;
  });

  test('H.1: Unauthenticated API access is strictly rejected', async ({ request }) => {
    // No Authorization header
    const res1 = await request.get('http://127.0.0.1:8000/api/v1/projects');
    expect(res1.status()).toBe(401);

    const res2 = await request.get(`http://127.0.0.1:8000/api/v1/projects/${projectAId}`);
    expect(res2.status()).toBe(401);

    const res3 = await request.get(`http://127.0.0.1:8000/api/v1/prd/${projectAId}`);
    expect(res3.status()).toBe(401);
  });

  test('H.2: Invalid token access is rejected', async ({ request }) => {
    const fakeToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature';
    const res = await request.get('http://127.0.0.1:8000/api/v1/projects', {
      headers: { Authorization: `Bearer ${fakeToken}` }
    });
    expect(res.status()).toBe(401);
  });

  test('H.3: Cross-user project access is blocked (User B accessing User A project)', async ({ request }) => {
    const res = await request.get(`http://127.0.0.1:8000/api/v1/projects/${projectAId}`, {
      headers: { Authorization: `Bearer ${tokenB}` }
    });
    // Strict multi-tenant isolation returns 404 (does not disclose existence to unauthorized tenant)
    expect(res.status()).toBe(404);
  });

  test('H.4: Cross-user PRD access and generation attempts are blocked', async ({ request }) => {
    // User B attempting to view PRD of User A
    const prdRes = await request.get(`http://127.0.0.1:8000/api/v1/prd/${projectAId}`, {
      headers: { Authorization: `Bearer ${tokenB}` }
    });
    expect(prdRes.status()).toBe(404);

    // User B attempting to trigger PRD generation on User A project
    const genRes = await request.post(`http://127.0.0.1:8000/api/v1/prd/${projectAId}/generate`, {
      headers: { Authorization: `Bearer ${tokenB}` }
    });
    expect(genRes.status()).toBe(404);
  });

  test('H.5: Cross-user document upload and export access is blocked', async ({ request }) => {
    // User B attempting to upload reference document into User A project
    const uploadRes = await request.post(`http://127.0.0.1:8000/api/v1/projects/${projectAId}/upload-reference`, {
      headers: { Authorization: `Bearer ${tokenB}` },
      multipart: {
        file: {
          name: 'injected.txt',
          mimeType: 'text/plain',
          buffer: Buffer.from('unauthorized file upload attempt')
        }
      }
    });
    expect(uploadRes.status()).toBe(404);

    // User B attempting to export User A PRD
    const exportRes = await request.get(`http://127.0.0.1:8000/api/v1/export/${projectAId}/markdown`, {
      headers: { Authorization: `Bearer ${tokenB}` }
    });
    expect(exportRes.status()).toBe(404);
  });
});

