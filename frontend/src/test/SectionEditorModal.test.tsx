import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SectionEditorModal } from '../components/SectionEditorModal';
import { PRDSectionContent } from '../types';

describe('SectionEditorModal Component', () => {
  const mockSection: PRDSectionContent = {
    key: 'functional_requirements',
    title: '12. Functional Requirements',
    content: 'Initial functional requirements markdown text',
    is_na: false,
    last_modified: new Date().toISOString()
  };

  it('renders section title and content when open', () => {
    render(
      <SectionEditorModal
        section={mockSection}
        isOpen={true}
        onClose={vi.fn()}
        onSave={vi.fn()}
        onRegenerate={vi.fn()}
      />
    );
    expect(screen.getByText('12. Functional Requirements')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Initial functional requirements markdown text')).toBeInTheDocument();
  });

  it('triggers onSave callback with updated content', async () => {
    const handleSave = vi.fn().mockResolvedValue(undefined);
    render(
      <SectionEditorModal
        section={mockSection}
        isOpen={true}
        onClose={vi.fn()}
        onSave={handleSave}
        onRegenerate={vi.fn()}
      />
    );

    const textarea = screen.getByDisplayValue('Initial functional requirements markdown text');
    fireEvent.change(textarea, { target: { value: 'Updated markdown content' } });

    const saveButton = screen.getByText('Save Changes');
    fireEvent.click(saveButton);

    expect(handleSave).toHaveBeenCalledWith(
      'functional_requirements',
      'Updated markdown content',
      false,
      ''
    );
  });
});
