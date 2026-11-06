import React, { useState, useEffect } from 'react';
import { PRDVersion } from '../../types';
import { X, Copy, Check, Hash, FileText, CheckCircle2, AlertTriangle, ShieldCheck, Tag, Info, Layers, Calendar, Terminal } from 'lucide-react';

interface DocumentDetailsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  prdVersion: PRDVersion;
  projectTitle: string;
  targetDomain?: string;
}

export const DocumentDetailsDrawer: React.FC<DocumentDetailsDrawerProps> = ({
  isOpen,
  onClose,
  prdVersion,
  projectTitle,
  targetDomain,
}) => {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sectionsList = Object.values(prdVersion.sections || {});
  const totalSections = sectionsList.length;
  const naSections = sectionsList.filter((s) => s.is_na).length;
  const activeSections = totalSections - naSections;

  // Real calculations based strictly on actual section contents
  let totalWords = 0;
  let frCount = 0;
  let nfrCount = 0;
  let acCount = 0;
  let brCount = 0;

  sectionsList.forEach((sec) => {
    if (sec.content && !sec.is_na) {
      totalWords += sec.content.split(/\s+/).filter(Boolean).length;
      frCount += (sec.content.match(/\bFR-\d+\b/g) || []).length;
      nfrCount += (sec.content.match(/\bNFR-\d+\b/g) || []).length;
      acCount += (sec.content.match(/\bAC-\d+\b/g) || []).length;
      brCount += (sec.content.match(/\bBR-\d+\b/g) || []).length;
    }
  });

  const isApproved = prdVersion.status?.toLowerCase() === 'approved';

  const handleCopyHash = () => {
    if (prdVersion.content_hash) {
      navigator.clipboard.writeText(prdVersion.content_hash);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end no-print animate-in fade-in duration-200">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <aside
        role="dialog"
        aria-label="Document Metadata and Specifications"
        className="relative z-50 w-full sm:max-w-md bg-white h-full shadow-2xl border-l border-slate-200 flex flex-col overflow-hidden animate-in slide-in-from-right duration-200"
      >
        {/* Drawer Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center space-x-2.5">
            <div className="p-1.5 bg-sky-100 text-sky-700 rounded-lg">
              <Info className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900 tracking-tight">Document Details</h2>
              <p className="text-[11px] text-slate-500">Metadata, structural metrics & technical audit</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-lg transition"
            aria-label="Close details drawer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Drawer Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Group 1: Essential Identity */}
          <section className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Identity & Lifecycle
            </h3>
            <div className="p-4 bg-slate-50/70 rounded-xl border border-slate-200/80 space-y-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Document Title</span>
                <span className="font-semibold text-slate-900 text-right truncate max-w-[200px]">
                  {projectTitle}
                </span>
              </div>
              <div className="flex items-center justify-between pt-2 border-t border-slate-200/60">
                <span className="text-slate-500">Version</span>
                <span className="font-mono font-bold text-slate-800 bg-white px-2 py-0.5 rounded border border-slate-200 text-[11px]">
                  {prdVersion.version_number}
                </span>
              </div>
              <div className="flex items-center justify-between pt-2 border-t border-slate-200/60">
                <span className="text-slate-500">Lifecycle Status</span>
                <span
                  className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${
                    isApproved
                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                      : 'bg-amber-100 text-amber-800 border border-amber-200'
                  }`}
                >
                  {isApproved ? (
                    <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  ) : (
                    <AlertTriangle className="w-3 h-3 text-amber-600" />
                  )}
                  <span>{prdVersion.status}</span>
                </span>
              </div>
              <div className="flex items-center justify-between pt-2 border-t border-slate-200/60">
                <span className="text-slate-500">Created Date</span>
                <span className="font-medium text-slate-700">
                  {new Date(prdVersion.created_at).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })}
                </span>
              </div>
              {targetDomain && (
                <div className="flex items-center justify-between pt-2 border-t border-slate-200/60">
                  <span className="text-slate-500">Target Domain</span>
                  <span className="font-medium text-slate-800">{targetDomain}</span>
                </div>
              )}
            </div>
          </section>

          {/* Group 2: Structural Metrics */}
          <section className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Structural Volume
            </h3>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-slate-50/70 rounded-xl border border-slate-200/80 text-center">
                <div className="text-xl font-bold text-slate-900">{totalSections}</div>
                <div className="text-[11px] text-slate-500 mt-0.5">Total Sections</div>
              </div>
              <div className="p-3 bg-slate-50/70 rounded-xl border border-slate-200/80 text-center">
                <div className="text-xl font-bold text-sky-700">{activeSections}</div>
                <div className="text-[11px] text-slate-500 mt-0.5">In-Scope Sections</div>
              </div>
            </div>

            <div className="p-3.5 bg-slate-50/70 rounded-xl border border-slate-200/80 space-y-2 text-xs">
              {naSections > 0 && (
                <div className="flex items-center justify-between text-slate-600">
                  <span>Marked Not Applicable</span>
                  <span className="font-semibold text-slate-800">{naSections}</span>
                </div>
              )}
              <div className="flex items-center justify-between text-slate-600">
                <span>Calculated Word Count</span>
                <span className="font-mono font-semibold text-slate-800">
                  {totalWords.toLocaleString()} words
                </span>
              </div>
            </div>
          </section>

          {/* Group 3: Traceability Breakdown */}
          <section className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Requirements Breakdown
            </h3>
            <div className="p-3.5 bg-slate-50/70 rounded-xl border border-slate-200/80 space-y-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-600 flex items-center space-x-1.5">
                  <Tag className="w-3.5 h-3.5 text-sky-500" />
                  <span>Functional Requirements (FR)</span>
                </span>
                <span className="font-mono font-bold text-slate-800 bg-white px-2 py-0.5 rounded border border-slate-200">
                  {frCount}
                </span>
              </div>
              <div className="flex items-center justify-between pt-2 border-t border-slate-200/60">
                <span className="text-slate-600 flex items-center space-x-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-indigo-500" />
                  <span>Non-Functional Requirements (NFR)</span>
                </span>
                <span className="font-mono font-bold text-slate-800 bg-white px-2 py-0.5 rounded border border-slate-200">
                  {nfrCount}
                </span>
              </div>
              <div className="flex items-center justify-between pt-2 border-t border-slate-200/60">
                <span className="text-slate-600 flex items-center space-x-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Acceptance Criteria (AC)</span>
                </span>
                <span className="font-mono font-bold text-slate-800 bg-white px-2 py-0.5 rounded border border-slate-200">
                  {acCount}
                </span>
              </div>
              <div className="flex items-center justify-between pt-2 border-t border-slate-200/60">
                <span className="text-slate-600 flex items-center space-x-1.5">
                  <FileText className="w-3.5 h-3.5 text-amber-500" />
                  <span>Business Rules (BR)</span>
                </span>
                <span className="font-mono font-bold text-slate-800 bg-white px-2 py-0.5 rounded border border-slate-200">
                  {brCount}
                </span>
              </div>
            </div>
          </section>

          {/* Group 4: Technical Identifiers & Cryptographic Hash */}
          <section className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Audit & Provenance
            </h3>
            <div className="p-3.5 bg-slate-50/70 rounded-xl border border-slate-200/80 space-y-2.5 text-xs">
              {prdVersion.id && (
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Version ID</span>
                  <span className="font-mono text-[11px] text-slate-700 truncate max-w-[180px]">
                    {prdVersion.id}
                  </span>
                </div>
              )}
              {prdVersion.job_id && (
                <div className="flex items-center justify-between pt-2 border-t border-slate-200/60">
                  <span className="text-slate-500">Job ID</span>
                  <span className="font-mono text-[11px] text-slate-700 truncate max-w-[180px]">
                    {prdVersion.job_id}
                  </span>
                </div>
              )}

              {prdVersion.content_hash && (
                <div className="pt-2 border-t border-slate-200/60 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 flex items-center space-x-1">
                      <Hash className="w-3 h-3 text-slate-400" />
                      <span>SHA-256 Digest</span>
                    </span>
                    <button
                      onClick={handleCopyHash}
                      className="inline-flex items-center space-x-1 text-[11px] text-sky-600 hover:text-sky-800 font-semibold"
                      title="Copy SHA-256 Hash"
                    >
                      {copied ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-600" />
                          <span className="text-emerald-600">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                  <div className="font-mono text-[10px] text-slate-600 break-all bg-white p-2 rounded border border-slate-200 select-all">
                    {prdVersion.content_hash}
                  </div>
                </div>
              )}
            </div>
          </section>
        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50/80 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg transition"
          >
            Close Details
          </button>
        </div>
      </aside>
    </div>
  );
};
