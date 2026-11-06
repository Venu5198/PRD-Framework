import React, { useState, useEffect } from 'react';
import { PRDVersion, PRDSectionContent } from '../../types';
import { DocumentToolbar } from './DocumentToolbar';
import { TableOfContents } from './TableOfContents';
import { DocumentDetailsDrawer } from './DocumentDetailsDrawer';
import { MarkdownRenderer } from './MarkdownRenderer';
import { SectionEditorModal } from '../SectionEditorModal';
import { FileText, CheckCircle2, Edit3, ArrowUp, Hash, Info, Calendar } from 'lucide-react';

interface PRDDocumentViewerProps {
  prdVersion: PRDVersion;
  projectTitle: string;
  targetDomain?: string;
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
  targetDomain,
  onBackToOverview,
  onExport,
  onSaveSection,
  onRegenerateSection,
  onRunValidation,
  validating = false,
}) => {
  const [activeSectionKey, setActiveSectionKey] = useState<string>('');
  const [isNavCollapsed, setIsNavCollapsed] = useState(false);
  const [mobileTocOpen, setMobileTocOpen] = useState(false);
  const [isDetailsOpen, setIsDetailsOpen] = useState(false);
  const [editingSection, setEditingSection] = useState<PRDSectionContent | null>(null);
  const [showScrollTop, setShowScrollTop] = useState(false);

  const sectionsList = Object.values(prdVersion.sections || {});

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

      const sectionElements = sectionsList
        .map((s) => ({ key: s.key, el: document.getElementById(`section-${s.key}`) }))
        .filter((item) => item.el !== null);

      const scrollPos = window.scrollY + 160;

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
      const topOffset = element.getBoundingClientRect().top + window.scrollY - 70;
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
    <div data-testid="prd-document-viewer" className="min-h-screen bg-slate-100/70 pb-20 text-slate-900">
      {/* 1. Compact Top Toolbar */}
      <DocumentToolbar
        projectTitle={projectTitle}
        versionNumber={prdVersion.version_number}
        status={prdVersion.status}
        onBackToOverview={onBackToOverview}
        onExport={onExport}
        onPrint={handlePrint}
        onToggleNav={() => {
          if (window.innerWidth < 1024) {
            setMobileTocOpen(!mobileTocOpen);
          } else {
            setIsNavCollapsed(!isNavCollapsed);
          }
        }}
        isNavCollapsed={isNavCollapsed}
        onOpenDetails={() => setIsDetailsOpen(true)}
        onRunValidation={onRunValidation}
        validating={validating}
      />

      {/* 2. Workspace Layout: Collapsible Left Nav + Large Center Document */}
      <div className="max-w-[1360px] mx-auto px-4 sm:px-6 md:px-8 pt-6 flex justify-center gap-6 xl:gap-8">
        {/* Left: Collapsible Table of Contents */}
        <TableOfContents
          sections={sectionsList}
          activeSectionKey={activeSectionKey}
          onSelectSection={handleSelectSection}
          isOpenMobile={mobileTocOpen}
          onCloseMobile={() => setMobileTocOpen(false)}
          isCollapsed={isNavCollapsed}
          onToggleCollapse={() => setIsNavCollapsed(true)}
        />

        {/* Center: Large Continuous Document Area (850-1000px readable width) */}
        <main className={`flex-1 min-w-0 transition-all duration-200 ${isNavCollapsed ? 'max-w-[1000px]' : 'max-w-[940px]'}`}>
          <article className="document-container bg-white shadow-xl rounded-2xl border border-slate-200/90 px-6 py-10 sm:px-12 sm:py-14 md:px-16 md:py-18 text-slate-800 transition-all">
            
            {/* Clean Document Cover & Summary */}
            <header className="border-b border-slate-200 pb-8 mb-10">
              <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
                <div className="flex items-center space-x-2 text-[11px] sm:text-xs uppercase tracking-widest text-sky-700 font-bold">
                  <FileText className="w-3.5 h-3.5 text-sky-600" />
                  <span>Product Requirements Document</span>
                </div>
                
                <button
                  onClick={() => setIsDetailsOpen(true)}
                  className="inline-flex items-center space-x-1 text-xs text-slate-500 hover:text-sky-600 font-medium transition"
                  title="View full document metadata and metrics"
                >
                  <Info className="w-3.5 h-3.5 text-slate-400" />
                  <span>Document Details</span>
                </button>
              </div>

              {/* Document Title: 28-32px bold */}
              <h1 className="text-[28px] sm:text-[32px] font-bold text-slate-900 tracking-tight leading-tight">
                {projectTitle}
              </h1>

              {/* Compact Document Summary Row */}
              <div className="mt-6 pt-5 border-t border-slate-100 flex flex-wrap items-center gap-x-6 gap-y-3 text-xs sm:text-[13px] text-slate-600">
                <div className="flex items-center space-x-2">
                  <span className="text-slate-400 font-medium">Version:</span>
                  <span className="font-mono font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded text-xs">
                    {prdVersion.version_number}
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  <span className="text-slate-400 font-medium">Status:</span>
                  <span className={`inline-flex items-center space-x-1 font-semibold ${isApproved ? 'text-emerald-700' : 'text-amber-700'}`}>
                    {isApproved && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />}
                    <span className="capitalize">{prdVersion.status}</span>
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  <span className="text-slate-400 font-medium">Date:</span>
                  <span className="font-medium text-slate-700">
                    {new Date(prdVersion.created_at).toLocaleDateString(undefined, {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric'
                    })}
                  </span>
                </div>

                {targetDomain && (
                  <div className="flex items-center space-x-2">
                    <span className="text-slate-400 font-medium">Domain:</span>
                    <span className="font-medium text-slate-800">{targetDomain}</span>
                  </div>
                )}

                <div className="flex items-center space-x-2 sm:ml-auto">
                  <span className="text-slate-400 font-medium">Scope:</span>
                  <span className="font-semibold text-slate-700">{sectionsList.length} Canonical Sections</span>
                </div>
              </div>
            </header>

            {/* Continuous Sections Stream */}
            <div className="space-y-12">
              {sectionsList.map((sec) => {
                return (
                  <section
                    key={sec.key}
                    id={`section-${sec.key}`}
                    className="scroll-mt-20 group relative"
                  >
                    {/* Section Header (22-24px bold) */}
                    <div className="flex items-center justify-between pb-2 mb-4 border-b border-slate-200">
                      <h2 className="text-[22px] sm:text-[24px] font-bold text-slate-900 tracking-tight">
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
                      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs sm:text-[13.5px] text-slate-500 italic">
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
          className="fixed bottom-6 right-6 p-2.5 bg-slate-900 text-white rounded-full shadow-lg hover:bg-slate-800 transition-all z-20 no-print"
          title="Scroll to top"
          aria-label="Scroll to top"
        >
          <ArrowUp className="w-4 h-4" />
        </button>
      )}

      {/* Collapsible Document Details Drawer */}
      <DocumentDetailsDrawer
        isOpen={isDetailsOpen}
        onClose={() => setIsDetailsOpen(false)}
        prdVersion={prdVersion}
        projectTitle={projectTitle}
        targetDomain={targetDomain}
      />

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
