export interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  role: string;
  created_at: string;
}

export interface Project {
  id: string;
  title: string;
  description?: string;
  target_domain?: string;
  owner_id: string;
  active_prd_id?: string;
  created_at: string;
  updated_at: string;
}

export interface Submission {
  id: string;
  project_id: string;
  submission_type: string;
  raw_idea: string;
  problem_statement?: string;
  assignment_context?: string;
  target_audience?: string;
  technical_constraints?: string;
  file_attachments: string[];
  created_at: string;
}

export interface AssignmentRequirement {
  instruction: string;
  mandatory_sections: string[];
  deliverables: string[];
  constraints: string[];
  expected_length?: string;
}

export interface AnalysisRecord {
  id?: string;
  project_id: string;
  product_category: string;
  problem_domain: string;
  intended_users: string[];
  core_objectives: string[];
  expected_capabilities: string[];
  explicit_constraints: string[];
  missing_critical_info: string[];
  facts: string[];
  assumptions: string[];
  assignment_requirements?: AssignmentRequirement;
  created_at: string;
}

export interface ClarificationQuestion {
  id: string;
  priority: 'critical' | 'medium' | 'low';
  category: string;
  question: string;
  rationale: string;
  suggested_options: string[];
  user_answer?: string;
  resolved_as_assumption: boolean;
  documented_assumption?: string;
}

export interface ClarificationSession {
  id?: string;
  project_id: string;
  questions: ClarificationQuestion[];
  status: 'pending' | 'in_progress' | 'completed';
  created_at: string;
}

export interface PRDSectionContent {
  key: string;
  title: string;
  content: string;
  is_na: boolean;
  na_rationale?: string;
  last_modified: string;
}

export interface PRDVersion {
  id: string;
  prd_id: string;
  project_id: string;
  version_number: string;
  status: 'draft' | 'approved' | 'archived';
  sections: Record<string, PRDSectionContent>;
  changelog: string;
  created_at: string;
  created_by: string;
}

export interface ValidationIssue {
  rule_id: string;
  severity: 'error' | 'warning' | 'info';
  section_key?: string;
  title: string;
  description: string;
  recommendation: string;
}

export interface ValidationReport {
  id: string;
  prd_version_id: string;
  project_id: string;
  is_valid: boolean;
  score: number;
  total_issues: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  issues: ValidationIssue[];
  created_at: string;
}

export interface SystemHealth {
  status: string;
  version: string;
  database: {
    connected: boolean;
    is_in_memory_mock: boolean;
  };
  ai_engine: {
    type: string;
    available: boolean;
    default_model: string;
  };
}

