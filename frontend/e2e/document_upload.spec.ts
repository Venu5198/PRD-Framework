import { test, expect } from './fixtures';

test.describe('Scenario D: Document Upload and File Security Workflows', () => {
  let projectId: string;
  let authToken: string;

  test.beforeEach(async ({ monitoredPage, testUser, request }) => {
    const { page } = monitoredPage;

    // Login user via API to obtain token
    const loginRes = await request.post('http://127.0.0.1:8000/api/v1/auth/login', {
      data: { username: testUser.username, password: testUser.password }
    });
    const tokenData = await loginRes.json();
    authToken = tokenData.access_token;

    // Create a project for uploads
    const projRes = await request.post('http://127.0.0.1:8000/api/v1/projects', {
      headers: { Authorization: `Bearer ${authToken}` },
      data: {
        title: `Upload Test Project ${Date.now()}`,
        description: 'Testing file validations and security limits',
        target_domain: 'General Software'
      }
    });
    const proj = await projRes.json();
    projectId = proj.id;

    // Log into UI
    await page.goto('/');
    await page.fill('input[type="text"]:near(:text("Username"))', testUser.username);
    await page.fill('input[type="password"]', testUser.password);
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Idea in. Professional PRD out.')).toBeVisible({ timeout: 15000 });
  });

  test('D.1: Valid TXT and Markdown uploads', async ({ request }) => {
    // Test valid .txt upload
    const txtRes = await request.post(`http://127.0.0.1:8000/api/v1/projects/${projectId}/upload-reference`, {
      headers: { Authorization: `Bearer ${authToken}` },
      multipart: {
        file: {
          name: 'requirements.txt',
          mimeType: 'text/plain',
          buffer: Buffer.from('Core system functional requirements content.')
        }
      }
    });
    expect(txtRes.status()).toBe(200);
    const txtData = await txtRes.json();
    expect(txtData.status).toBe('uploaded');

    // Test valid .md upload
    const mdRes = await request.post(`http://127.0.0.1:8000/api/v1/projects/${projectId}/upload-reference`, {
      headers: { Authorization: `Bearer ${authToken}` },
      multipart: {
        file: {
          name: 'spec.md',
          mimeType: 'text/markdown',
          buffer: Buffer.from('# Architecture Specification\n\nDetailed markdown specification.')
        }
      }
    });
    expect(mdRes.status()).toBe(200);
    const mdData = await mdRes.json();
    expect(mdData.status).toBe('uploaded');
  });

  test('D.2: Valid PDF and DOCX uploads', async ({ request }) => {
    // Test valid .pdf upload
    const pdfRes = await request.post(`http://127.0.0.1:8000/api/v1/projects/${projectId}/upload-reference`, {
      headers: { Authorization: `Bearer ${authToken}` },
      multipart: {
        file: {
          name: 'assignment.pdf',
          mimeType: 'application/pdf',
          buffer: Buffer.from('%PDF-1.4 mock pdf document content for requirements')
        }
      }
    });
    expect(pdfRes.status()).toBe(200);
    const pdfData = await pdfRes.json();
    expect(pdfData.status).toBe('uploaded');

    // Test valid .docx upload
    const docxRes = await request.post(`http://127.0.0.1:8000/api/v1/projects/${projectId}/upload-reference`, {
      headers: { Authorization: `Bearer ${authToken}` },
      multipart: {
        file: {
          name: 'document.docx',
          mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          buffer: Buffer.from('PK\x03\x04 mock docx binary content')
        }
      }
    });
    expect(docxRes.status()).toBe(200);
    const docxData = await docxRes.json();
    expect(docxData.status).toBe('uploaded');
  });

  test('D.3: Unsupported file extension rejection', async ({ request }) => {
    const exeRes = await request.post(`http://127.0.0.1:8000/api/v1/projects/${projectId}/upload-reference`, {
      headers: { Authorization: `Bearer ${authToken}` },
      multipart: {
        file: {
          name: 'malware.exe',
          mimeType: 'application/x-msdownload',
          buffer: Buffer.from('malicious script')
        }
      }
    });
    expect(exeRes.status()).toBe(400);
    const err = await exeRes.json();
    expect(err.detail).toContain('Unsupported file extension');
  });

  test('D.4: Oversized file rejection (>15 MB)', async ({ request }) => {
    // 16 MB buffer
    const bigBuffer = Buffer.alloc(16 * 1024 * 1024, 'A');
    const bigRes = await request.post(`http://127.0.0.1:8000/api/v1/projects/${projectId}/upload-reference`, {
      headers: { Authorization: `Bearer ${authToken}` },
      multipart: {
        file: {
          name: 'oversized.txt',
          mimeType: 'text/plain',
          buffer: bigBuffer
        }
      }
    });
    expect(bigRes.status()).toBe(413);
  });

  test('D.5: Empty file rejection (0 bytes)', async ({ request }) => {
    const emptyRes = await request.post(`http://127.0.0.1:8000/api/v1/projects/${projectId}/upload-reference`, {
      headers: { Authorization: `Bearer ${authToken}` },
      multipart: {
        file: {
          name: 'empty.txt',
          mimeType: 'text/plain',
          buffer: Buffer.alloc(0)
        }
      }
    });
    expect(emptyRes.status()).toBe(400);
    const err = await emptyRes.json();
    expect(err.detail).toContain('Cannot upload an empty file');
  });

  test('D.6: Executable disguise rejection (MZ header)', async ({ request }) => {
    // File named as .pdf but starting with Windows PE 'MZ' magic bytes
    const fakePdfRes = await request.post(`http://127.0.0.1:8000/api/v1/projects/${projectId}/upload-reference`, {
      headers: { Authorization: `Bearer ${authToken}` },
      multipart: {
        file: {
          name: 'trojan.pdf',
          mimeType: 'application/pdf',
          buffer: Buffer.from('MZ\x90\x00\x03\x00\x00\x00')
        }
      }
    });
    expect(fakePdfRes.status()).toBe(400);
    const err = await fakePdfRes.json();
    expect(err.detail).toContain('Executable files are forbidden');
  });

  test('D.7: Path traversal filename sanitation', async ({ request }) => {
    const traversalRes = await request.post(`http://127.0.0.1:8000/api/v1/projects/${projectId}/upload-reference`, {
      headers: { Authorization: `Bearer ${authToken}` },
      multipart: {
        file: {
          name: '../../../../etc/passwd.txt',
          mimeType: 'text/plain',
          buffer: Buffer.from('root:x:0:0:root:/root:/bin/bash')
        }
      }
    });
    expect(traversalRes.status()).toBe(200);
    const resData = await traversalRes.json();
    // Verify filename is strictly sanitized to basename without ../
    expect(resData.filename).toBe('passwd.txt');
    expect(resData.stored_path).not.toContain('..');
  });

  test('D.8: Filename containing special characters and spaces', async ({ request }) => {
    const specialRes = await request.post(`http://127.0.0.1:8000/api/v1/projects/${projectId}/upload-reference`, {
      headers: { Authorization: `Bearer ${authToken}` },
      multipart: {
        file: {
          name: 'my complex document (v1.0) & final #1.pdf',
          mimeType: 'application/pdf',
          buffer: Buffer.from('%PDF-1.4 test special characters')
        }
      }
    });
    expect(specialRes.status()).toBe(200);
    const resData = await specialRes.json();
    expect(resData.status).toBe('uploaded');
  });
});

