import {
  User,
  Project,
  Submission,
  AnalysisRecord,
  ClarificationSession,
  PRDVersion,
  ValidationReport,
  SystemHealth,
  Job,
  JobCreateResponse
} from '../types';

const API_BASE = '/api/v1';

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        if (token) {
          window.localStorage.setItem('auth_token', token);
        } else {
          window.localStorage.removeItem('auth_token');
        }
      }
    } catch (_) {}
  }

  getToken(): string | null {
    if (!this.token) {
      try {
        if (typeof window !== 'undefined' && window.localStorage) {
          this.token = window.localStorage.getItem('auth_token');
        }
      } catch (_) {}
    }
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    const token = this.getToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }

    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers
    });

    if (!res.ok) {
      let errorMsg = `HTTP Error ${res.status}`;
      try {
        const errJson = await res.json();
        errorMsg = errJson.detail || errorMsg;
      } catch (_) {}
      throw new Error(errorMsg);
    }

    return res.json();
  }

  // System
  async getHealth(): Promise<SystemHealth> {
    return this.request<SystemHealth>('/system/health');
  }

  async getModels(): Promise<{ active_model: string; available_models: any[] }> {
    return this.request('/system/models');
  }

  async selectModel(model: string): Promise<any> {
    return this.request('/system/models/select', {
      method: 'POST',
      body: JSON.stringify({ model })
    });
  }

  // Auth
  async login(username: string, password: string): Promise<{ access_token: string }> {
    const res = await this.request<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    this.setToken(res.access_token);
    return res;
  }

  async register(username: string, email: string, password: string, fullName?: string): Promise<User> {
    return this.request<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, email, password, full_name: fullName })
    });
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  // Projects
  async getProjects(): Promise<Project[]> {
    return this.request<Project[]>('/projects');
  }

  async createProject(title: string, description?: string, targetDomain?: string): Promise<Project> {
    return this.request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({ title, description, target_domain: targetDomain })
    });
  }

  async getProject(projectId: string): Promise<Project> {
    return this.request<Project>(`/projects/${projectId}`);
  }

  // Submissions
  async submitIdea(
    projectId: string,
    submissionType: string,
    rawIdea: string,
    problemStatement?: string,
    assignmentContext?: string
  ): Promise<Submission> {
    return this.request<Submission>(`/projects/${projectId}/submissions`, {
      method: 'POST',
      body: JSON.stringify({
        submission_type: submissionType,
        raw_idea: rawIdea,
        problem_statement: problemStatement,
        assignment_context: assignmentContext
      })
    });
  }

  async uploadReferenceFile(projectId: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.request(`/projects/${projectId}/upload-reference`, {
      method: 'POST',
      body: formData
    });
  }

  // Analysis & Clarifications
  async analyzeProject(projectId: string): Promise<AnalysisRecord> {
    return this.request<AnalysisRecord>(`/analysis/${projectId}/analyze`, {
      method: 'POST'
    });
  }

  async getAnalysis(projectId: string): Promise<AnalysisRecord> {
    return this.request<AnalysisRecord>(`/analysis/${projectId}/analysis`);
  }

  async generateClarifications(projectId: string): Promise<ClarificationSession> {
    return this.request<ClarificationSession>(`/analysis/${projectId}/clarifications/generate`, {
      method: 'POST'
    });
  }

  async getClarifications(projectId: string): Promise<ClarificationSession> {
    return this.request<ClarificationSession>(`/analysis/${projectId}/clarifications`);
  }

  async answerClarification(
    projectId: string,
    questionId: string,
    answer?: string,
    proceedWithAssumption: boolean = false
  ): Promise<any> {
    return this.request(`/analysis/${projectId}/clarifications/answer`, {
      method: 'POST',
      body: JSON.stringify({
        question_id: questionId,
        answer,
        proceed_with_assumption: proceedWithAssumption
      })
    });
  }

  // PRD Asynchronous Generation Jobs
  async startPRDGeneration(projectId: string, useMock: boolean = false): Promise<JobCreateResponse> {
    return this.request<JobCreateResponse>(`/projects/${projectId}/prd/generate?use_mock=${useMock}`, {
      method: 'POST'
    });
  }

  async getJob(jobId: string): Promise<Job> {
    return this.request<Job>(`/jobs/${jobId}`);
  }

  async getJobResult(jobId: string): Promise<PRDVersion> {
    return this.request<PRDVersion>(`/jobs/${jobId}/result`);
  }

  async cancelJob(jobId: string): Promise<{ job_id: string; status: string; message: string }> {
    return this.request(`/jobs/${jobId}/cancel`, {
      method: 'POST'
    });
  }

  async getActivePRDJob(projectId: string): Promise<Job | null> {
    return this.request<Job | null>(`/projects/${projectId}/prd/job`);
  }

  // PRD Synchronous fallback
  async generatePRD(projectId: string): Promise<PRDVersion> {
    return this.request<PRDVersion>(`/prd/${projectId}/generate`, {
      method: 'POST'
    });
  }

  async getActivePRD(projectId: string): Promise<{ document: any; active_version: PRDVersion | null }> {
    return this.request(`/prd/${projectId}`);
  }

  async getPRDVersions(projectId: string): Promise<PRDVersion[]> {
    return this.request<PRDVersion[]>(`/prd/${projectId}/versions`);
  }

  async updateSection(
    projectId: string,
    sectionKey: string,
    content: string,
    isNa: boolean = false,
    naRationale?: string
  ): Promise<PRDVersion> {
    return this.request<PRDVersion>(`/prd/${projectId}/sections/${sectionKey}`, {
      method: 'PATCH',
      body: JSON.stringify({
        content,
        is_na: isNa,
        na_rationale: naRationale
      })
    });
  }

  async regenerateSection(
    projectId: string,
    sectionKey: string,
    guidance?: string
  ): Promise<PRDVersion> {
    return this.request<PRDVersion>(`/prd/${projectId}/sections/${sectionKey}/regenerate`, {
      method: 'POST',
      body: JSON.stringify({ guidance })
    });
  }

  async approveVersion(projectId: string, versionId: string): Promise<PRDVersion> {
    return this.request<PRDVersion>(`/prd/${projectId}/versions/${versionId}/approve`, {
      method: 'POST'
    });
  }

  // Validation
  async validatePRD(projectId: string, versionId?: string): Promise<ValidationReport> {
    const query = versionId ? `?version_id=${encodeURIComponent(versionId)}` : '';
    return this.request<ValidationReport>(`/validation/${projectId}/validate${query}`, {
      method: 'POST'
    });
  }

  async getValidationReport(projectId: string, versionId?: string): Promise<ValidationReport> {
    const query = versionId ? `?version_id=${encodeURIComponent(versionId)}` : '';
    return this.request<ValidationReport>(`/validation/${projectId}/report${query}`);
  }

  // Export URLs & Download Trigger
  getExportUrl(projectId: string, format: 'markdown' | 'docx' | 'pdf', versionId?: string): string {
    const token = this.getToken();
    const params = new URLSearchParams();
    if (token) params.set('token', token);
    if (versionId) params.set('version_id', versionId);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return `${API_BASE}/export/${projectId}/${format}${qs}`;
  }

  async downloadExport(projectId: string, format: 'markdown' | 'docx' | 'pdf', filename?: string, versionId?: string): Promise<void> {
    const token = this.getToken();
    const qs = versionId ? `?version_id=${encodeURIComponent(versionId)}` : '';
    const res = await fetch(`${API_BASE}/export/${projectId}/${format}${qs}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    if (!res.ok) {
      throw new Error(`Export download failed with HTTP status ${res.status}`);
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const defaultExt = format === 'markdown' ? 'md' : format;
    a.download = filename || `PRD_${projectId}.${defaultExt}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  }
}

export const api = new ApiClient();

