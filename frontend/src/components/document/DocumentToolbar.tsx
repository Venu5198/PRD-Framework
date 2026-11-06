import React from 'react';
import { ArrowLeft, Download, Printer, CheckCircle2, AlertTriangle, Menu, PanelLeftClose, PanelLeft, FileText, Info, RefreshCw } from 'lucide-react';

interface DocumentToolbarProps {
  projectTitle: string;
  versionNumber: string;
  status: string;
  onBackToOverview: () => void;
  onExport: (format: 'markdown' | 'pdf' | 'docx') => void;
  onPrint: () => void;
  onToggleNav: () => void;
  isNavCollapsed: boolean;
  onOpenDetails: () => void;
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
  onToggleNav,
  isNavCollapsed,
  onOpenDetails,
  onRunValidation,
  validating = false,
}) => {
  const isApproved = status.toLowerCase() === 'approved';

  return (
    <header className="sticky top-0 z-30 bg-slate-900 text-white border-b border-slate-800 shadow-sm document-toolbar no-print">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 h-13 flex items-center justify-between gap-3">
        {/* Left Side: Navigation Toggle, Back, Title, Version, Status */}
        <div className="flex items-center space-x-3 min-w-0">
          {/* Toggle Sidebar Navigation */}
          <button
            onClick={onToggleNav}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition shrink-0"
            title={isNavCollapsed ? "Show Document Outline" : "Collapse Document Outline"}
            aria-label="Toggle Document Outline"
          >
            {isNavCollapsed ? (
              <PanelLeft className="w-4 h-4 text-sky-400" />
            ) : (
              <PanelLeftClose className="w-4 h-4 text-slate-300" />
            )}
          </button>

          {/* Back to Projects */}
          <button
            onClick={onBackToOverview}
            className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition shrink-0"
            title="Return to Project Dashboard"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Projects</span>
          </button>

          <div className="h-4 w-px bg-slate-700 hidden sm:block shrink-0" />

          {/* Title & Status */}
          <div className="flex items-center space-x-2 truncate min-w-0">
            <span className="text-xs sm:text-sm font-bold text-white truncate max-w-[160px] sm:max-w-[280px] md:max-w-[380px]">
              {projectTitle}
            </span>
            <span className="px-2 py-0.5 bg-slate-800 text-sky-400 text-[11px] font-mono font-bold rounded border border-slate-700 shrink-0">
              {versionNumber}
            </span>
            <span
              className={`inline-flex items-center space-x-1 px-2 py-0.5 text-[11px] font-semibold rounded-full shrink-0 ${
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

        {/* Right Side: Details Drawer, Validate, Grouped Exports, Print */}
        <div className="flex items-center space-x-2 shrink-0">
          {/* Document Details Trigger */}
          <button
            onClick={onOpenDetails}
            className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition border border-slate-700"
            title="View Document Details, Stats & Technical Identifiers"
          >
            <Info className="w-3.5 h-3.5 text-sky-400" />
            <span className="hidden md:inline">Details</span>
          </button>

          {/* Validation Trigger */}
          {onRunValidation && (
            <button
              onClick={onRunValidation}
              disabled={validating}
              className="inline-flex items-center space-x-1 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition border border-slate-700 disabled:opacity-50"
              title="Run Automated Quality & Semantic Validation"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-sky-400 ${validating ? 'animate-spin' : ''}`} />
              <span className="hidden lg:inline">Validate</span>
            </button>
          )}

          {/* Grouped Export Buttons */}
          <div className="flex items-center rounded-lg bg-slate-800 border border-slate-700 p-0.5" role="group" aria-label="Export Formats">
            <button
              onClick={() => onExport('markdown')}
              className="px-2.5 py-1 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-700 rounded transition"
              title="Export Clean Markdown (.md)"
            >
              MD
            </button>
            <button
              onClick={() => onExport('docx')}
              className="px-2.5 py-1 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-700 rounded transition"
              title="Export Microsoft Word (.docx)"
            >
              DOCX
            </button>
            <button
              onClick={() => onExport('pdf')}
              className="px-2.5 py-1 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-700 rounded transition"
              title="Export PDF Document (.pdf)"
            >
              PDF
            </button>
          </div>

          {/* Print Action */}
          <button
            onClick={onPrint}
            className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition border border-slate-700"
            title="Print or Save via Browser"
          >
            <Printer className="w-3.5 h-3.5 text-slate-300" />
            <span className="hidden sm:inline">Print</span>
          </button>
        </div>
      </div>
    </header>
  );
};
