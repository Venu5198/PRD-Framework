import React, { useState, useRef, useEffect } from 'react';
import {
  ArrowLeft,
  Download,
  Printer,
  CheckCircle2,
  AlertTriangle,
  PanelLeftClose,
  PanelLeft,
  FileText,
  Info,
  RefreshCw,
  MoreVertical,
  FileDown
} from 'lucide-react';

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
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const isApproved = status.toLowerCase() === 'approved';

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };

    if (menuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleEscape);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [menuOpen]);

  return (
    <header className="sticky top-0 z-30 bg-slate-900 text-white border-b border-slate-800 shadow-sm document-toolbar no-print">
      <div className="max-w-[1400px] mx-auto px-2 sm:px-6 h-14 flex items-center justify-between gap-2 sm:gap-3">
        {/* Left Side: Navigation Toggle, Back, Title, Version, Status */}
        <div className="flex items-center space-x-1.5 sm:space-x-3 min-w-0">
          {/* Toggle Sidebar Navigation */}
          <button
            onClick={onToggleNav}
            className="min-h-[44px] min-w-[44px] p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition flex items-center justify-center shrink-0"
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
            className="min-h-[44px] px-2.5 sm:px-3 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition inline-flex items-center space-x-1.5 shrink-0"
            title="Return to Project Dashboard"
            aria-label="Back to Projects"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">Projects</span>
          </button>

          <div className="h-4 w-px bg-slate-700 hidden sm:block shrink-0" />

          {/* Title & Status */}
          <div className="flex items-center space-x-1.5 sm:space-x-2 truncate min-w-0">
            <span className="text-xs sm:text-sm font-bold text-white truncate max-w-[110px] xs:max-w-[150px] sm:max-w-[260px] md:max-w-[360px]">
              {projectTitle}
            </span>
            <span className="px-1.5 sm:px-2 py-0.5 bg-slate-800 text-sky-400 text-[10px] sm:text-[11px] font-mono font-bold rounded border border-slate-700 shrink-0">
              {versionNumber}
            </span>
            <span
              className={`inline-flex items-center space-x-1 px-1.5 sm:px-2 py-0.5 text-[10px] sm:text-[11px] font-semibold rounded-full shrink-0 ${
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
              <span className="capitalize hidden xs:inline">{status}</span>
            </span>
          </div>
        </div>

        {/* Right Side Actions */}
        <div className="flex items-center space-x-1.5 sm:space-x-2 shrink-0">
          {/* Validation Trigger (Always visible) */}
          {onRunValidation && (
            <button
              onClick={onRunValidation}
              disabled={validating}
              className="min-h-[44px] px-2.5 sm:px-3 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition border border-slate-700 disabled:opacity-50 inline-flex items-center space-x-1.5 shrink-0"
              title="Run Automated Quality & Semantic Validation"
              aria-label="Validate PRD"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-sky-400 ${validating ? 'animate-spin' : ''}`} />
              <span className="hidden lg:inline">Validate</span>
            </button>
          )}

          {/* Desktop Only: Document Details Trigger */}
          <button
            onClick={onOpenDetails}
            className="hidden md:inline-flex min-h-[44px] items-center space-x-1.5 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition border border-slate-700"
            title="View Document Details, Stats & Technical Identifiers"
          >
            <Info className="w-3.5 h-3.5 text-sky-400" />
            <span>Details</span>
          </button>

          {/* Desktop Only: Grouped Export Buttons */}
          <div className="hidden md:flex items-center rounded-lg bg-slate-800 border border-slate-700 p-0.5" role="group" aria-label="Export Formats">
            <button
              onClick={() => onExport('markdown')}
              className="px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-700 rounded transition"
              title="Export Clean Markdown (.md)"
            >
              MD
            </button>
            <button
              onClick={() => onExport('docx')}
              className="px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-700 rounded transition"
              title="Export Microsoft Word (.docx)"
            >
              DOCX
            </button>
            <button
              onClick={() => onExport('pdf')}
              className="px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-700 rounded transition"
              title="Export PDF Document (.pdf)"
            >
              PDF
            </button>
          </div>

          {/* Desktop Only: Print Action */}
          <button
            onClick={onPrint}
            className="hidden md:inline-flex min-h-[44px] items-center space-x-1.5 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition border border-slate-700"
            title="Print or Save via Browser"
          >
            <Printer className="w-3.5 h-3.5 text-slate-300" />
            <span>Print</span>
          </button>

          {/* Mobile/Tablet Only: Primary PDF Export */}
          <button
            onClick={() => onExport('pdf')}
            className="md:hidden min-h-[44px] px-3 bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold rounded-lg transition inline-flex items-center space-x-1.5 shadow-sm"
            title="Download PDF"
            aria-label="Download PDF"
          >
            <Download className="w-3.5 h-3.5" />
            <span>PDF</span>
          </button>

          {/* Mobile/Tablet Only: Overflow Dropdown */}
          <div className="relative md:hidden" ref={menuRef}>
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="min-h-[44px] min-w-[44px] p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition flex items-center justify-center border border-slate-700"
              title="More actions"
              aria-label="More document actions"
              aria-expanded={menuOpen}
            >
              <MoreVertical className="w-4 h-4" />
            </button>

            {menuOpen && (
              <div
                role="menu"
                className="absolute right-0 mt-2 w-48 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl py-1 z-50 text-xs text-slate-200 animate-in fade-in-50 zoom-in-95 duration-100"
              >
                <button
                  role="menuitem"
                  onClick={() => {
                    setMenuOpen(false);
                    onOpenDetails();
                  }}
                  className="w-full text-left px-3.5 py-2.5 hover:bg-slate-700 flex items-center space-x-2 transition"
                >
                  <Info className="w-3.5 h-3.5 text-sky-400" />
                  <span>Document Details</span>
                </button>
                <div className="h-px bg-slate-700 my-1" />
                <button
                  role="menuitem"
                  onClick={() => {
                    setMenuOpen(false);
                    onExport('markdown');
                  }}
                  className="w-full text-left px-3.5 py-2.5 hover:bg-slate-700 flex items-center space-x-2 transition"
                >
                  <FileDown className="w-3.5 h-3.5 text-slate-400" />
                  <span>Export Markdown (.md)</span>
                </button>
                <button
                  role="menuitem"
                  onClick={() => {
                    setMenuOpen(false);
                    onExport('docx');
                  }}
                  className="w-full text-left px-3.5 py-2.5 hover:bg-slate-700 flex items-center space-x-2 transition"
                >
                  <FileDown className="w-3.5 h-3.5 text-slate-400" />
                  <span>Export Word (.docx)</span>
                </button>
                <div className="h-px bg-slate-700 my-1" />
                <button
                  role="menuitem"
                  onClick={() => {
                    setMenuOpen(false);
                    onPrint();
                  }}
                  className="w-full text-left px-3.5 py-2.5 hover:bg-slate-700 flex items-center space-x-2 transition"
                >
                  <Printer className="w-3.5 h-3.5 text-slate-400" />
                  <span>Print Document</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
