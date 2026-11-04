import React, { useState } from 'react';
import { PRDSectionContent } from '../types';
import { Sparkles, Save, X, RefreshCw } from 'lucide-react';

interface SectionEditorModalProps {
  section: PRDSectionContent;
  isOpen: boolean;
  onClose: () => void;
  onSave: (key: string, content: string, isNa: boolean, naRationale?: string) => Promise<void>;
  onRegenerate: (key: string, guidance?: string) => Promise<void>;
}

export const SectionEditorModal: React.FC<SectionEditorModalProps> = ({
  section,
  isOpen,
  onClose,
  onSave,
  onRegenerate,
}) => {
  const [content, setContent] = useState(section.content);
  const [isNa, setIsNa] = useState(section.is_na);
  const [naRationale, setNaRationale] = useState(section.na_rationale || '');
  const [guidance, setGuidance] = useState('');
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  if (!isOpen) return null;

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(section.key, content, isNa, naRationale);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      await onRegenerate(section.key, guidance);
      onClose();
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full flex flex-col max-h-[90vh] border border-slate-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <div>
            <h3 className="text-lg font-bold text-slate-900">{section.title}</h3>
            <p className="text-xs text-slate-500">Edit section content or regenerate with local AI</p>
          </div>
          <button onClick={onClose} className="p-1 rounded-md text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="isNa"
              checked={isNa}
              onChange={(e) => setIsNa(e.target.checked)}
              className="rounded border-slate-300 text-sky-600 focus:ring-sky-500 w-4 h-4"
            />
            <label htmlFor="isNa" className="text-sm font-medium text-slate-700">
              Mark this section as Not Applicable (N/A)
            </label>
          </div>

          {isNa ? (
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">
                Reason / Rationale for N/A
              </label>
              <input
                type="text"
                value={naRationale}
                onChange={(e) => setNaRationale(e.target.value)}
                placeholder="e.g. Mobile client not required for server-only backend scope"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-sky-500"
              />
            </div>
          ) : (
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">
                Section Content (Markdown)
              </label>
              <textarea
                rows={12}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                className="w-full p-3 font-mono text-xs leading-relaxed border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:outline-none"
              />
            </div>
          )}

          {/* AI Regeneration Bar */}
          <div className="bg-sky-50/70 p-4 rounded-lg border border-sky-100 space-y-2">
            <div className="flex items-center space-x-2 text-xs font-semibold text-sky-800">
              <Sparkles className="w-4 h-4 text-sky-600" />
              <span>Regenerate with Local AI Model</span>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={guidance}
                onChange={(e) => setGuidance(e.target.value)}
                placeholder="Optional adjustment guidance (e.g. Add stricter performance metrics and 3 edge cases)"
                className="flex-1 px-3 py-1.5 text-xs border border-slate-300 rounded-md focus:ring-2 focus:ring-sky-500 bg-white"
              />
              <button
                type="button"
                onClick={handleRegenerate}
                disabled={regenerating}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-sky-600 text-white rounded-md text-xs font-medium hover:bg-sky-700 transition disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${regenerating ? 'animate-spin' : ''}`} />
                <span>{regenerating ? 'Regenerating...' : 'Regenerate Section'}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3 bg-slate-50 border-t border-slate-200 rounded-b-xl">
          <span className="text-xs text-slate-500">
            Saving creates a new minor version (e.g., v1.1) to preserve history.
          </span>
          <div className="flex space-x-2">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center space-x-1.5 px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-medium hover:bg-slate-800 transition disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>{saving ? 'Saving...' : 'Save Changes'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

