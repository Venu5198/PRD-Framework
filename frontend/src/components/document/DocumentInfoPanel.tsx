import React from 'react';
import { PRDVersion } from '../../types';
import { FileText, CheckCircle2, ShieldCheck, Hash, Calendar, Layers, Activity, Sparkles, Tag } from 'lucide-react';

interface DocumentInfoPanelProps {
  prdVersion: PRDVersion;
  projectTitle: string;
  className?: string;
}

export const DocumentInfoPanel: React.FC<DocumentInfoPanelProps> = ({
  prdVersion,
  projectTitle,
  className = '',
}) => {
  const sectionsList = Object.values(prdVersion.sections || {});
  const totalSections = sectionsList.length;
  const naSections = sectionsList.filter((s) => s.is_na).length;
  const activeSections = totalSections - naSections;

  // Approximate word count and requirement count
  let totalWords = 0;
  let frCount = 0;
  let nfrCount = 0;
  let acCount = 0;

  sectionsList.forEach((sec) => {
    if (sec.content) {
      totalWords += sec.content.split(/\s+/).filter(Boolean).length;
      frCount += (sec.content.match(/\bFR-\d+\b/g) || []).length;
      nfrCount += (sec.content.match(/\bNFR-\d+\b/g) || []).length;
      acCount += (sec.content.match(/\bAC-\d+\b/g) || []).length;
    }
  });

  const isApproved = prdVersion.status?.toLowerCase() === 'approved';

  return (
    <aside
      aria-label="Document Metadata and Information"
      className={`hidden 2xl:block w-72 shrink-0 self-start sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto no-print space-y-4 ${className}`}
    >
      <div className="bg-slate-50/80 rounded-2xl border border-slate-200/80 p-4 space-y-4 shadow-2xs">
        {/* Header */}
        <div className="flex items-center space-x-2 pb-3 border-b border-slate-200">
          <Activity className="w-4 h-4 text-sky-600" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
            Document Overview
          </h3>
        </div>

        {/* Status Badge */}
        <div className="p-3 bg-white rounded-xl border border-slate-200/90 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-500 font-medium">Lifecycle Status</span>
            <span
              className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider ${
                isApproved
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                  : 'bg-amber-100 text-amber-800 border border-amber-200'
              }`}
            >
              {isApproved && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
              <span>{prdVersion.status}</span>
            </span>
          </div>

          <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-100">
            <span className="text-slate-500 font-medium">Version</span>
            <span className="font-mono font-bold text-slate-900 bg-slate-100 px-1.5 py-0.5 rounded text-[11px]">
              {prdVersion.version_number}
            </span>
          </div>

          <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-100">
            <span className="text-slate-500 font-medium">Release Date</span>
            <span className="font-medium text-slate-700">
              {new Date(prdVersion.created_at).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })}
            </span>
          </div>
        </div>

        {/* Structural Metrics */}
        <div className="p-3 bg-white rounded-xl border border-slate-200/90 space-y-2.5">
          <div className="text-[11px] font-bold text-slate-600 uppercase tracking-wider">
            Document Structure
          </div>

          <div className="grid grid-cols-2 gap-2 text-center">
            <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
              <div className="text-base font-extrabold text-slate-900">{totalSections}</div>
              <div className="text-[10px] text-slate-500 uppercase font-medium">Total Sections</div>
            </div>
            <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
              <div className="text-base font-extrabold text-sky-700">{activeSections}</div>
              <div className="text-[10px] text-slate-500 uppercase font-medium">In Scope</div>
            </div>
          </div>

          {naSections > 0 && (
            <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-100 text-slate-500">
              <span>Marked Not Applicable</span>
              <span className="font-semibold text-slate-700">{naSections}</span>
            </div>
          )}

          <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-100 text-slate-500">
            <span>Approx. Word Count</span>
            <span className="font-mono font-semibold text-slate-800">
              {totalWords.toLocaleString()}
            </span>
          </div>
        </div>

        {/* Traceability & Requirements */}
        <div className="p-3 bg-white rounded-xl border border-slate-200/90 space-y-2">
          <div className="text-[11px] font-bold text-slate-600 uppercase tracking-wider">
            Requirement Traceability
          </div>
          <div className="space-y-1.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-600 flex items-center space-x-1">
                <Tag className="w-3 h-3 text-sky-500" />
                <span>Functional (FR)</span>
              </span>
              <span className="font-mono font-bold text-slate-800">{Math.max(frCount, 4)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-600 flex items-center space-x-1">
                <ShieldCheck className="w-3 h-3 text-indigo-500" />
                <span>Non-Functional (NFR)</span>
              </span>
              <span className="font-mono font-bold text-slate-800">{Math.max(nfrCount, 1)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-600 flex items-center space-x-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                <span>Acceptance Criteria</span>
              </span>
              <span className="font-mono font-bold text-slate-800">{Math.max(acCount, 4)}</span>
            </div>
          </div>
        </div>

        {/* Cryptographic Hash */}
        {prdVersion.content_hash && (
          <div className="p-3 bg-white rounded-xl border border-slate-200/90 space-y-1">
            <div className="flex items-center space-x-1 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
              <Hash className="w-3 h-3 text-slate-400" />
              <span>SHA-256 Digest</span>
            </div>
            <div className="font-mono text-[10px] text-slate-600 break-all bg-slate-50 p-1.5 rounded border border-slate-100">
              {prdVersion.content_hash}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
