import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from '../api/client';

describe('ApiClient Unit Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('generates correct export URLs for markdown, docx, and pdf', () => {
    expect(api.getExportUrl('proj-123', 'markdown')).toBe('/api/v1/export/proj-123/markdown');
    expect(api.getExportUrl('proj-123', 'docx')).toBe('/api/v1/export/proj-123/docx');
    expect(api.getExportUrl('proj-123', 'pdf')).toBe('/api/v1/export/proj-123/pdf');
  });

  it('sets and retrieves local token', () => {
    api.setToken('test-jwt-token-xyz');
    expect(api.getToken()).toBe('test-jwt-token-xyz');
    api.setToken(null);
    expect(api.getToken()).toBeNull();
  });
});
