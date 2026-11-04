import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ValidationBadge } from '../components/ValidationBadge';
import { ValidationReport } from '../types';

describe('ValidationBadge Component', () => {
  it('renders pending badge when report is null', () => {
    render(<ValidationBadge report={null} />);
    expect(screen.getByText('Validation Pending')).toBeInTheDocument();
  });

  it('renders green score and passing metrics when score >= 80', () => {
    const mockReport: ValidationReport = {
      id: 'val-1',
      prd_version_id: 'v1.0',
      project_id: 'p1',
      is_valid: true,
      score: 95,
      total_issues: 0,
      error_count: 0,
      warning_count: 0,
      info_count: 0,
      issues: [],
      created_at: new Date().toISOString()
    };
    render(<ValidationBadge report={mockReport} />);
    expect(screen.getByText('Quality Score: 95/100')).toBeInTheDocument();
  });

  it('renders errors and warnings when detected', () => {
    const mockReport: ValidationReport = {
      id: 'val-2',
      prd_version_id: 'v1.0',
      project_id: 'p1',
      is_valid: false,
      score: 65,
      total_issues: 3,
      error_count: 1,
      warning_count: 2,
      info_count: 0,
      issues: [],
      created_at: new Date().toISOString()
    };
    render(<ValidationBadge report={mockReport} />);
    expect(screen.getByText('Quality Score: 65/100')).toBeInTheDocument();
    expect(screen.getByText('1 Errors')).toBeInTheDocument();
    expect(screen.getByText('2 Warnings')).toBeInTheDocument();
  });
});

