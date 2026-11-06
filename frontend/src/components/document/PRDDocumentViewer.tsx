import React, { useState, useEffect, useRef } from 'react';
import { PRDVersion, PRDSectionContent } from '../../types';
import { DocumentToolbar } from './DocumentToolbar';
import { TableOfContents } from './TableOfContents';
import { MarkdownRenderer } from './MarkdownRenderer';
import { SectionEditorModal } from '../SectionEditorModal';
import { FileText, Calendar, Hash, ShieldCheck, CheckCircle2, Edit3, ArrowUp } from 'lucide-react';

interface PRDDocumentViewerProps {
  prdVersion: PRDVersion;
  projectTitle: string;
  onBackToOverview: () => void;
  onExport: (format: 'markdown' | 'pdf' | 'docx') => void;
  onSaveSection: (key: string, content: string, isNa: boolean, naRationale?: string) => Promise<void>;
  onRegenerateSection: (key: string, guidance?: string) => Promise<void>;
  onRunValidation?: () => void;
  validating?: boolean;
}

export const PRDDocumentViewer: React.FC<PRDDocumentViewerProps> = ({
  prdVersion,
  projectTitle,
  onBackToOverview,
  onExport,
  onSaveSection,
  onRegenerateSection,
  onRunValidation,
  validating = false,
}) => {
  const [activeSectionKey, setActiveSectionKey] = useState<string>('');
  const [mobileTocOpen, setMobileTocOpen] = useState(false);
  const [editingSection, setEditingSection] = useState<PRDSectionContent | null>(null);
  const [showScrollTop, setShowScrollTop] = useState(false);

  const sectionsList = Object.values(prdVersion.sections);

  // Initialize active section key
  useEffect(() => {
    if (sectionsList.length > 0 && !activeSectionKey) {
      setActiveSectionKey(sectionsList[0].key);
    }
  }, [sectionsList, activeSectionKey]);

  // Track scrolling for active TOC item and back-to-top button
  useEffect(() => {
    const handleScroll = () => {
      setShowScrollTop(window.scrollY > 400);

      // Find section currently in view
      const sectionElements = sectionsList
        .map((s) => ({ key: s.key, el: document.getElementById(`section-${s.key}`) }))
        .filter((item) => item.el !== null);

      const scrollPos = window.scrollY + 180;

      for (let i = sectionElements.length - 1; i >= 0; i--) {
        const item = sectionElements[i];
        if (item.el && item.el.offsetTop <= scrollPos) {
          setActiveSectionKey(item.key);
          break;
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [sectionsList]);

  const handleSelectSection = (key: string) => {
    setActiveSectionKey(key);
    const element = document.getElementById(`section-${key}`);
    if (element) {
      const topOffset = element.getBoundingClientRect().top + window.scrollY - 80;
      window.scrollTo({ top: topOffset, behavior: 'smooth' });
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const isApproved = prdVersion.status?.toLowerCase() === 'approved';

  return (
    <div data-testid="prd-document-viewer" className="min-h-screen bg-slate-100/70 pb-20">
      {/* 1. Document Toolbar */}
      <DocumentToolbar
        projectTitle={projectTitle}
        versionNumber={prdVersion.version_number}
        status={prdVersion.status}
        onBackToOverview={onBackToOverview}
        onExport={onExport}
        onPrint={handlePrint}
        onToggleMobileToc={() => setMobileTocOpen(true)}
        onRunValidation={onRunValidation}
        validating={validating}
      />

      {/* 2. Main Workspace Layout */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-8 flex gap-8">
        {/* Left: Table of Contents */}
        <TableOfContents
          sections={sectionsList}
          activeSectionKey={activeSectionKey}
          onSelectSection={handleSelectSection}
          isOpenMobile={mobileTocOpen}
          onCloseMobile={() => setMobileTocOpen(false)}
        />

        {/* Center: Continuous Document Container */}
        <main className="flex-1 min-w-0">
          <article className="document-container bg-white shadow-xl rounded-2xl border border-slate-200/80 max-w-[920px] mx-auto px-6 py-10 sm:px-12 sm:py-16 md:px-16 md:py-20 text-slate-800 transition-all">
            
            {/* Document Header & Cover Information */}
            <header className="border-b border-slate-200 pb-10 mb-12">
              <div className="flex items-center space-x-2 text-xs uppercase tracking-widest text-sky-700 font-bold mb-3">
                <FileText className="w-4 h-4 text-sky-600" />
                <span>Product Requirements Document (PRD)</span>
              </div>

              <h1 className="text-3xl sm:text-4xl md:text-[42px] font-extrabold text-slate-900 tracking-tight leading-tight">
                {projectTitle}
              </h1>

              <p className="text-base sm:text-lg text-slate-500 mt-2 font-normal">
                Technical Specification & System Architecture Baseline
              </p>

              {/* Metadata Grid */}
              <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-xl bg-slate-50/80 border border-slate-200/70 text-xs">
                <div>
                  <span className="text-slate-400 font-medium block">Document Version</span>
                  <span className="font-bold text-slate-800 font-mono text-sm">{prdVersion.version_number}</span>
                </div>
                <div>
                  <span className="text-slate-400 font-medium block">Lifecycle Status</span>
                  <span className={`inline-flex items-center space-x-1 font-bold ${isApproved ? 'text-emerald-700' : 'text-amber-700'}`}>
                    {isApproved && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />}
                    <span className="capitalize">{prdVersion.status}</span>
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 font-medium block">Creation Date</span>
                  <span className="font-medium text-slate-700">
                    {new Date(prdVersion.created_at).toLocaleDateString(undefined, {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric'
                    })}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 font-medium block">Canonical Sections</span>
                  <span className="font-bold text-slate-800">{sectionsList.length} of 27 Specified</span>
                </div>
              </div>

              {prdVersion.content_hash && (
                <div className="mt-3 flex items-center space-x-2 text-[11px] text-slate-500 font-mono">
                  <Hash className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span className="truncate">Content Hash (SHA-256): {prdVersion.content_hash}</span>
                </div>
              )}
            </header>

            {/* Continuous Sections Stream */}
            <div className="space-y-12">
              {sectionsList.map((sec, idx) => {
                return (
                  <section
                    key={sec.key}
                    id={`section-${sec.key}`}
                    className="scroll-mt-24 group relative"
                  >
                    {/* Section Header with subtle quick edit trigger */}
                    <div className="flex items-center justify-between pb-2 mb-4 border-b border-slate-200">
                      <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                        {sec.title}
                      </h2>
                      <div className="flex items-center space-x-2">
                        {sec.is_na && (
                          <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-bold uppercase border border-slate-200">
                            Not Applicable
                          </span>
                        )}
                        <button
                          onClick={() => setEditingSection(sec)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 text-slate-400 hover:text-sky-600 hover:bg-sky-50 rounded-md text-xs inline-flex items-center space-x-1 no-print"
                          title={`Edit ${sec.title}`}
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                          <span className="hidden sm:inline text-[11px] font-semibold">Edit</span>
                        </button>
                      </div>
                    </div>

                    {/* Section Content */}
                    {sec.is_na ? (
                      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs sm:text-sm text-slate-500 italic">
                        Marked as Not Applicable: {sec.na_rationale || 'Omitted from baseline product scope'}
                      </div>
                    ) : (
                      <MarkdownRenderer content={sec.content} />
                    )}
                  </section>
                );
              })}
            </div>

            {/* Document Footer */}
            <footer className="mt-20 pt-8 border-t border-slate-200 text-center text-xs text-slate-400 space-y-1">
              <p className="font-medium text-slate-500">
                End of Product Requirements Document — {projectTitle}
              </p>
              <p>Generated by Local-First Automated PRD Engineering Framework</p>
            </footer>
          </article>
        </main>
      </div>

      {/* Floating Scroll To Top Button */}
      {showScrollTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-6 right-6 p-3 bg-slate-900 text-white rounded-full shadow-lg hover:bg-slate-800 transition-all z-20 no-print"
          title="Scroll to top"
        >
          <ArrowUp className="w-4 h-4" />
        </button>
      )}

      {/* Section Editor Modal */}
      {editingSection && (
        <SectionEditorModal
          section={editingSection}
          isOpen={true}
          onClose={() => setEditingSection(null)}
          onSave={onSaveSection}
          onRegenerate={onRegenerateSection}
        />
      )}
    </div>
  );
};
