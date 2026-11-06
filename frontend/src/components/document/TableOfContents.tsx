import React, { useState } from 'react';
import { PRDSectionContent } from '../../types';
import { Search, ChevronRight, X, BookOpen, PanelLeftClose } from 'lucide-react';

interface TableOfContentsProps {
  sections: PRDSectionContent[];
  activeSectionKey: string;
  onSelectSection: (key: string) => void;
  isOpenMobile?: boolean;
  onCloseMobile?: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const TableOfContents: React.FC<TableOfContentsProps> = ({
  sections,
  activeSectionKey,
  onSelectSection,
  isOpenMobile = false,
  onCloseMobile,
  isCollapsed = false,
  onToggleCollapse,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredSections = sections.filter((sec) =>
    sec.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const content = (
    <div className="flex flex-col h-full bg-slate-50/80 rounded-2xl border border-slate-200/80 p-3.5 shadow-2xs">
      {/* Outline Header with Collapse toggle */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-200">
        <div className="flex items-center space-x-2">
          <BookOpen className="w-4 h-4 text-sky-600" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
            Document Outline
          </h3>
        </div>
        <div className="flex items-center space-x-1.5">
          <span className="text-[10px] font-mono px-2 py-0.5 bg-slate-200/80 text-slate-700 rounded-full font-bold">
            {sections.length} Secs
          </span>
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className="hidden lg:inline-flex p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 rounded transition"
              title="Collapse Outline"
              aria-label="Collapse Document Outline"
            >
              <PanelLeftClose className="w-3.5 h-3.5" />
            </button>
          )}
          {onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="lg:hidden p-1 text-slate-400 hover:text-slate-600 rounded-md"
              aria-label="Close Mobile Outline"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Filter / Search Input */}
      <div className="my-2.5 relative">
        <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Filter sections..."
          className="w-full pl-8 pr-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500 transition"
        />
        {searchTerm && (
          <button
            onClick={() => setSearchTerm('')}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
          >
            <X className="w-3 h-3" />
          </button>
        )}
      </div>

      {/* Scrollable Section List */}
      <div className="flex-1 overflow-y-auto space-y-0.5 pr-1 scrollbar-thin">
        {filteredSections.map((sec) => {
          const isActive = activeSectionKey === sec.key;
          const match = sec.title.match(/^(\d+)\.\s*(.*)$/);
          const secNum = match ? match[1] : '';
          const secTitle = match ? match[2] : sec.title;

          return (
            <button
              key={sec.key}
              onClick={() => {
                onSelectSection(sec.key);
                if (onCloseMobile) onCloseMobile();
              }}
              className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium transition flex items-center justify-between group ${
                isActive
                  ? 'bg-sky-600 text-white font-semibold shadow-xs'
                  : 'text-slate-600 hover:bg-slate-200/70 hover:text-slate-900'
              }`}
            >
              <div className="flex items-center space-x-2 truncate">
                {secNum && (
                  <span
                    className={`font-mono text-[11px] shrink-0 ${
                      isActive ? 'text-sky-100 font-bold' : 'text-slate-400'
                    }`}
                  >
                    {secNum.padStart(2, '0')}
                  </span>
                )}
                <span className="truncate">{secTitle}</span>
              </div>
              {sec.is_na ? (
                <span
                  className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase shrink-0 ${
                    isActive ? 'bg-sky-700 text-sky-200' : 'bg-slate-200 text-slate-500'
                  }`}
                >
                  N/A
                </span>
              ) : (
                <ChevronRight
                  className={`w-3.5 h-3.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity ${
                    isActive ? 'opacity-100 text-sky-200' : 'text-slate-400'
                  }`}
                />
              )}
            </button>
          );
        })}
        {filteredSections.length === 0 && (
          <div className="py-6 text-center text-xs text-slate-400 italic">
            No sections match '{searchTerm}'
          </div>
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar (Width 240px when open, hidden when collapsed) */}
      {!isCollapsed && (
        <nav
          aria-label="Table of Contents"
          className="hidden lg:block w-[240px] xl:w-[260px] shrink-0 self-start sticky top-16 max-h-[calc(100vh-5rem)] table-of-contents no-print"
        >
          {content}
        </nav>
      )}

      {/* Mobile Drawer (Overlay, slide in from left) */}
      {isOpenMobile && (
        <div className="lg:hidden fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex no-print">
          <div className="w-[280px] max-w-[85vw] bg-white h-full p-4 shadow-2xl flex flex-col animate-in slide-in-from-left duration-200">
            {content}
          </div>
          <div className="flex-1" onClick={onCloseMobile} />
        </div>
      )}
    </>
  );
};
