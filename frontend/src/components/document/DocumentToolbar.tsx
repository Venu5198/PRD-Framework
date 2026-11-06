import React from 'react';
import { ArrowLeft, Download, Printer, CheckCircle2, AlertTriangle, Menu, FileText, Sparkles, RefreshCw } from 'lucide-react';

interface DocumentToolbarProps {
  projectTitle: string;
  versionNumber: string;
  status: string;
  onBackToOverview: () => void;
  onExport: (format: 'markdown' | 'pdf' | 'docx') => void;
  onPrint: () => void;
  onToggleMobileToc: () => void;
  onRunValidation?: () => void;
  validating?: boolean;
}

export const DocumentToolbar: React.FC<DocumentToolbarProps> = ({
  projectTitle,
  versionNumber,
  status,
  onBackToOverview,
  onExport,
  onPrint,
  onToggleMobileToc,
  onRunValidation,
  validating = false,
}) => {
  const isApproved = status.toLowerCase() === 'approved';

  return (
    <header className="sticky top-0 z-30 bg-slate-900/95 backdrop-blur-md text-white border-b border-slate-800 shadow-md document-toolbar no-print">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2.5 flex items-center justify-between flex-wrap gap-3">
        {/* Left: Navigation and Document Metadata */}
        <div className="flex items-center space-x-3">
          <button
            onClick={onToggleMobileToc}
            className="lg:hidden p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition"
            title="Open Table of Contents"
            aria-label="Toggle Table of Contents"
          >
            <Menu className="w-4 h-4" />
          </button>

          <button
            onClick={onBackToOverview}
            className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Project Stages</span>
          </button>

          <div className="h-4 w-px bg-slate-700 hidden sm:block" />

          <div className="flex items-center space-x-2 truncate">
            <span className="text-xs sm:text-sm font-bold text-white truncate max-w-[200px] sm:max-w-[320px]">
              {projectTitle}
            </span>
            <span className="px-2 py-0.5 bg-slate-800 text-sky-400 text-[11px] font-mono font-bold rounded-md border border-slate-700">
              {versionNumber}
            </span>
            <span
              className={`inline-flex items-center space-x-1 px-2 py-0.5 text-[11px] font-semibold rounded-full ${
                isApproved
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                  : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
              }`}
            >
              {isApproved ? (
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              ) : (
                <AlertTriangle className="w-3 h-3 text-amber-400" />
              )}
              <span className="capitalize">{status}</span>
            </span>
          </div>
        </div>

        {/* Right: Actions (Validation, Export, Print) */}
        <div className="flex items-center space-x-2">
          {onRunValidation && (
            <button
              onClick={onRunValidation}
              disabled={validating}
              className="inline-flex items-center space-x-1 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition border border-slate-700"
              title="Run automated validation"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-sky-400 ${validating ? 'animate-spin' : ''}`} />
              <span className="hidden md:inline">Validate</span>
            </button>
          )}

          <div className="flex items-center rounded-lg bg-slate-800 border border-slate-700 p-0.5">
            <button
              onClick={() => onExport('markdown')}
              className="px-2.5 py-1 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-700 rounded transition"
              title="Export as Markdown (.md)"
            >
              MD
            </button>
            <button
              onClick={() => onExport('docx')}
              className="px-2.5 py-1 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-700 rounded transition"
              title="Export as Microsoft Word (.docx)"
            >
              DOCX
            </button>
            <button
              onClick={() => onExport('pdf')}
              className="px-2.5 py-1 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-700 rounded transition"
              title="Export as PDF (.pdf)"
            >
              PDF
            </button>
          </div>

          <button
            onClick={onPrint}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition border border-slate-700"
            title="Print or Save to PDF via Browser"
          >
            <Printer className="w-3.5 h-3.5 text-slate-300" />
            <span className="hidden sm:inline">Print</span>
          </button>
        </div>
      </div>
    </header>
  );
};

