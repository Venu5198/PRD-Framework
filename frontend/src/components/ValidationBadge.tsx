import React from 'react';
import { ValidationReport } from '../types';
import { ShieldCheck, ShieldAlert, AlertTriangle, Info } from 'lucide-react';

export const ValidationBadge: React.FC<{ report: ValidationReport | null }> = ({ report }) => {
  if (!report) {
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
        <span>Validation Pending</span>
      </span>
    );
  }

  const isGreen = report.is_valid && report.score >= 80;
  const isYellow = report.score >= 60 && !isGreen;

  return (
    <div className="flex items-center space-x-2">
      <span
        className={`inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
          isGreen
            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
            : isYellow
            ? 'bg-amber-50 text-amber-700 border-amber-200'
            : 'bg-rose-50 text-rose-700 border-rose-200'
        }`}
      >
        {isGreen ? (
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
        ) : (
          <ShieldAlert className="w-4 h-4 text-rose-600" />
        )}
        <span>Quality Score: {report.score}/100</span>
      </span>

      {report.error_count > 0 && (
        <span className="inline-flex items-center space-x-1 text-xs font-semibold text-rose-600 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
          <span>{report.error_count} Errors</span>
        </span>
      )}
      {report.warning_count > 0 && (
        <span className="inline-flex items-center space-x-1 text-xs font-semibold text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
          <span>{report.warning_count} Warnings</span>
        </span>
      )}
    </div>
  );
};

