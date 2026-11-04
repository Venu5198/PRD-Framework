import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthPage } from '../pages/AuthPage';
import { Dashboard } from '../pages/Dashboard';
import { ProjectView } from '../pages/ProjectView';
import { api } from '../api/client';
import { AuthProvider } from '../context/AuthContext';

vi.mock('../api/client', () => ({
  api: {
    getMe: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    getProjects: vi.fn(),
    createProject: vi.fn(),
    getHealth: vi.fn(),
    getProject: vi.fn(),
    getAnalysis: vi.fn(),
    getClarifications: vi.fn(),
    getActivePRD: vi.fn(),
    getPRDVersions: vi.fn(),
    getValidationReport: vi.fn(),
    submitIdea: vi.fn(),
    analyzeProject: vi.fn(),
    generateClarifications: vi.fn(),
    answerClarification: vi.fn(),
    generatePRD: vi.fn(),
    validatePRD: vi.fn(),
    updateSection: vi.fn(),
    regenerateSection: vi.fn(),
    approveVersion: vi.fn(),
    getExportUrl: vi.fn((pid, fmt) => `/api/v1/export/${pid}/${fmt}`)
  }
}));

describe('Critical User Workflow Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1. Authentication Flow
  it('renders auth page and switches between sign in and registration', async () => {
    render(
      <AuthProvider>
        <AuthPage />
      </AuthProvider>
    );

    expect(screen.getByText('Sign In Locally')).toBeInTheDocument();
    const toggleButton = screen.getByText("Don't have an account? Register");
    fireEvent.click(toggleButton);

    expect(screen.getByText('Register Account')).toBeInTheDocument();
    expect(screen.getByText('Full Name')).toBeInTheDocument();
  });

  // 2. Project Creation Flow
  it('renders dashboard and creates a new project', async () => {
    vi.mocked(api.getProjects).mockResolvedValue([
      {
        id: 'p1',
        title: 'Existing App',
        description: 'Test app',
        target_domain: 'General Software',
        owner_id: 'u1',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
    ]);
    vi.mocked(api.getHealth).mockResolvedValue({
      status: 'healthy',
      version: '1.0.0',
      database: { connected: true, is_in_memory_mock: false },
      ai_engine: { type: 'OllamaAdapter', available: true, default_model: 'llama3.2' }
    });
    vi.mocked(api.createProject).mockResolvedValue({
      id: 'p2',
      title: 'New PRD Project',
      description: 'Brand new project',
      target_domain: 'General Software',
      owner_id: 'u1',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });

    const handleSelect = vi.fn();
    render(<Dashboard onSelectProject={handleSelect} />);

    await waitFor(() => {
      expect(screen.getByText('Existing App')).toBeInTheDocument();
    });

    // Open create modal
    const createBtn = screen.getByText('New PRD Project');
    fireEvent.click(createBtn);

    expect(screen.getByText('Create New PRD Project')).toBeInTheDocument();
    const input = screen.getByPlaceholderText('e.g. NextGen Micro-SaaS Platform');
    fireEvent.change(input, { target: { value: 'New PRD Project' } });

    const submitBtn = screen.getByText('Create & Proceed');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.createProject).toHaveBeenCalledWith('New PRD Project', '', 'General Software');
      expect(handleSelect).toHaveBeenCalledWith('p2');
    });
  });

  // 3. Idea Submission & Clarification Workflow
  it('renders project view, submits idea, and answers clarification questions', async () => {
    vi.mocked(api.getProject).mockResolvedValue({
      id: 'proj-123',
      title: 'Local First AI Suite',
      owner_id: 'u1',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
    vi.mocked(api.getAnalysis).mockResolvedValue({
      id: 'an-1',
      project_id: 'proj-123',
      product_category: 'Productivity',
      problem_domain: 'Engineering',
      intended_users: ['Software Engineers'],
      core_objectives: ['Automate PRDs'],
      expected_capabilities: ['Export'],
      explicit_constraints: ['Local-only'],
      missing_critical_info: [],
      facts: ['Submitted concept'],
      assumptions: ['Desktop environment'],
      created_at: new Date().toISOString()
    });
    vi.mocked(api.getClarifications).mockResolvedValue({
      id: 'cl-1',
      project_id: 'proj-123',
      status: 'pending',
      questions: [
        {
          id: 'CQ-001',
          priority: 'critical',
          category: 'Deployment',
          question: 'What is the primary target deployment environment?',
          rationale: 'Needed for architecture sizing',
          suggested_options: ['Single-user workstation', 'Local network server'],
          resolved_as_assumption: false
        }
      ],
      created_at: new Date().toISOString()
    });
    vi.mocked(api.getActivePRD).mockResolvedValue({
      document: { id: 'prd-1', project_id: 'proj-123' },
      active_version: null
    });
    vi.mocked(api.getPRDVersions).mockResolvedValue([]);
    vi.mocked(api.getValidationReport).mockRejectedValue(new Error('No report'));

    render(<ProjectView projectId="proj-123" onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('Local First AI Suite')).toBeInTheDocument();
    });

    // Switch to Clarifications tab
    const clarTab = screen.getByText('3. Clarifications');
    fireEvent.click(clarTab);

    expect(screen.getByText('What is the primary target deployment environment?')).toBeInTheDocument();
    expect(screen.getByText('+ Single-user workstation')).toBeInTheDocument();

    // Click suggested option and save
    fireEvent.click(screen.getByText('+ Single-user workstation'));
    const saveAnswerBtn = screen.getByText('Save Answer');
    fireEvent.click(saveAnswerBtn);

    expect(api.answerClarification).toHaveBeenCalledWith(
      'proj-123',
      'CQ-001',
      'Single-user workstation',
      false
    );
  });

  // 4. PRD Generation, Validation, and Export View
  it('renders generated PRD sections, validation report, and export links', async () => {
    vi.mocked(api.getProject).mockResolvedValue({
      id: 'proj-123',
      title: 'Local First AI Suite',
      owner_id: 'u1',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    });
    vi.mocked(api.getActivePRD).mockResolvedValue({
      document: { id: 'prd-1', project_id: 'proj-123' },
      active_version: {
        id: 'ver-1',
        prd_id: 'prd-1',
        project_id: 'proj-123',
        version_number: 'v1.0',
        status: 'draft',
        sections: {
          executive_summary: {
            key: 'executive_summary',
            title: '2. Executive Summary',
            content: 'Executive summary content describing local PRD generation.',
            is_na: false,
            last_modified: new Date().toISOString()
          }
        },
        changelog: 'Initial generation',
        created_at: new Date().toISOString(),
        created_by: 'u1'
      }
    });
    vi.mocked(api.getPRDVersions).mockResolvedValue([]);
    vi.mocked(api.getValidationReport).mockResolvedValue({
      id: 'rep-1',
      prd_version_id: 'ver-1',
      project_id: 'proj-123',
      is_valid: true,
      score: 95,
      total_issues: 0,
      error_count: 0,
      warning_count: 0,
      info_count: 0,
      issues: [],
      created_at: new Date().toISOString()
    });

    render(<ProjectView projectId="proj-123" onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('2. Executive Summary')).toBeInTheDocument();
      expect(screen.getByText('Executive summary content describing local PRD generation.')).toBeInTheDocument();
    });

    // Check Export tab
    const exportTab = screen.getByText('8. Export');
    fireEvent.click(exportTab);

    expect(screen.getByText('Markdown (.md)')).toBeInTheDocument();
    expect(screen.getByText('Microsoft Word (.docx)')).toBeInTheDocument();
    expect(screen.getByText('Adobe PDF (.pdf)')).toBeInTheDocument();
    expect(api.getExportUrl).toHaveBeenCalledWith('proj-123', 'markdown');
    expect(api.getExportUrl).toHaveBeenCalledWith('proj-123', 'docx');
    expect(api.getExportUrl).toHaveBeenCalledWith('proj-123', 'pdf');
  });
});
