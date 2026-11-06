import React from 'react';
import { MermaidViewer } from './MermaidViewer';
import { CheckCircle2, HelpCircle, Sparkles } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

// Inline formatting helper adhering to unified typography design tokens
export const renderInline = (text: string): React.ReactNode => {
  if (!text) return null;

  // Split by inline markdown patterns: **bold**, *italic*, `code`, [link](url), and Requirement IDs
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\)|(?:FR|NFR|BR|AC|RSK|CLM)-\d{3,4})/g;

  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      const inner = token.slice(2, -2);
      // Check for Gherkin keywords
      if (['Given', 'When', 'Then', 'And', 'But'].includes(inner.trim())) {
        parts.push(
          <span
            key={match.index}
            className="inline-block px-1.5 py-0.5 mr-1 text-[11px] font-bold rounded uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200"
          >
            {inner}
          </span>
        );
      } else {
        parts.push(
          <strong key={match.index} className="font-bold text-slate-900">
            {renderInline(inner)}
          </strong>
        );
      }
    } else if (token.startsWith('*') && token.endsWith('*')) {
      parts.push(
        <em key={match.index} className="italic text-slate-800">
          {renderInline(token.slice(1, -1))}
        </em>
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      const codeText = token.slice(1, -1);
      // Provenance classification badges
      if (['USER_CONFIRMED', 'ASSIGNMENT_REQUIRED', 'REFERENCE_SUPPORTED'].includes(codeText)) {
        parts.push(
          <span
            key={match.index}
            className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-emerald-50 text-emerald-800 border border-emerald-200"
          >
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            <span>{codeText}</span>
          </span>
        );
      } else if (['INFERRED', 'PROPOSED'].includes(codeText)) {
        parts.push(
          <span
            key={match.index}
            className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-sky-50 text-sky-800 border border-sky-200"
          >
            <Sparkles className="w-3 h-3 text-sky-600" />
            <span>{codeText}</span>
          </span>
        );
      } else if (['UNRESOLVED'].includes(codeText)) {
        parts.push(
          <span
            key={match.index}
            className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-50 text-amber-800 border border-amber-200"
          >
            <HelpCircle className="w-3 h-3 text-amber-600" />
            <span>{codeText}</span>
          </span>
        );
      } else {
        parts.push(
          <code
            key={match.index}
            className="px-1.5 py-0.5 rounded text-xs font-mono bg-slate-100 text-slate-800 border border-slate-200 font-medium"
          >
            {codeText}
          </code>
        );
      }
    } else if (token.startsWith('[') && token.includes('](')) {
      const linkMatch = token.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        parts.push(
          <a
            key={match.index}
            href={linkMatch[2]}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sky-600 hover:text-sky-800 underline underline-offset-2 font-medium"
          >
            {linkMatch[1]}
          </a>
        );
      } else {
        parts.push(token);
      }
    } else if (/^(?:FR|NFR|BR|AC|RSK|CLM)-\d{3,4}$/.test(token)) {
      parts.push(
        <span
          key={match.index}
          className="inline-block px-1.5 py-0.5 text-xs font-mono font-bold rounded bg-slate-100 text-slate-900 border border-slate-300"
        >
          {token}
        </span>
      );
    } else {
      parts.push(token);
    }

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return <>{parts}</>;
};

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '' }) => {
  if (!content) return null;

  const blocks: React.ReactNode[] = [];
  const lines = content.split('\n');
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // Skip empty lines
    if (!trimmed) {
      i++;
      continue;
    }

    // 1. Fenced Code Block / Mermaid
    if (trimmed.startsWith('```')) {
      const lang = trimmed.slice(3).trim().toLowerCase();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // consume closing ```
      const fullCode = codeLines.join('\n');

      if (lang === 'mermaid') {
        blocks.push(<MermaidViewer key={`block-${i}`} chart={fullCode} />);
      } else {
        blocks.push(
          <div key={`block-${i}`} className="my-5 rounded-xl border border-slate-200 overflow-hidden shadow-2xs">
            <div className="flex items-center justify-between px-4 py-2 bg-slate-800 text-slate-300 text-xs font-mono">
              <span>{lang || 'code'}</span>
            </div>
            <pre className="p-4 bg-slate-900 text-slate-100 font-mono text-xs sm:text-[13px] overflow-x-auto leading-relaxed">
              {fullCode}
            </pre>
          </div>
        );
      }
      continue;
    }

    // 2. Markdown Table
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i].trim());
        i++;
      }

      if (tableLines.length >= 2) {
        const rawHeaders = tableLines[0].split('|').slice(1, -1).map((c) => c.trim());
        const dataRows = tableLines.slice(2).map((rowLine) =>
          rowLine.split('|').slice(1, -1).map((c) => c.trim())
        );

        blocks.push(
          <div key={`block-${i}`} className="my-6 overflow-x-auto rounded-xl border border-slate-200/90 shadow-2xs">
            <table className="w-full text-left text-xs sm:text-[13px] border-collapse bg-white">
              <thead>
                <tr className="bg-slate-900 text-white border-b border-slate-700">
                  {rawHeaders.map((hdr, hIdx) => (
                    <th
                      key={hIdx}
                      className="px-4 py-3 font-semibold text-slate-100 tracking-wider text-xs border-r border-slate-800 last:border-r-0"
                    >
                      {renderInline(hdr)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {dataRows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-50/70 transition-colors even:bg-slate-50/40">
                    {row.map((cell, cIdx) => {
                      const isIdCol = cIdx === 0 || /^(?:FR|NFR|BR|AC|RSK|CLM)-\d+/.test(cell);
                      return (
                        <td
                          key={cIdx}
                          className={`px-4 py-2.5 text-slate-700 align-top leading-relaxed border-r border-slate-100 last:border-r-0 ${
                            isIdCol ? 'font-mono text-xs font-semibold text-slate-900' : ''
                          }`}
                        >
                          {renderInline(cell)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      continue;
    }

    // 3. Blockquotes / Callouts
    if (trimmed.startsWith('>')) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quoteLines.push(lines[i].trim().replace(/^>\s*/, ''));
        i++;
      }
      const quoteText = quoteLines.join(' ');
      const isNa = quoteText.includes('Not Applicable') || quoteText.includes('[Not Applicable');

      blocks.push(
        <div
          key={`block-${i}`}
          className={`my-4 p-4 rounded-r-xl border-l-4 text-xs sm:text-[13.5px] leading-relaxed ${
            isNa
              ? 'bg-slate-100/70 border-slate-400 text-slate-600 italic'
              : 'bg-sky-50/70 border-sky-500 text-sky-950 shadow-2xs'
          }`}
        >
          {renderInline(quoteText)}
        </div>
      );
      continue;
    }

    // 4. Headings (H1, H2, H3, H4) adhering to Typography Scale:
    // H1: 22-24px, H2: 18-20px, H3: 15-17px
    if (trimmed.startsWith('#### ')) {
      const text = trimmed.slice(5).trim();
      blocks.push(
        <h4 key={`block-${i}`} className="text-sm font-semibold text-slate-800 mt-5 mb-2 tracking-tight">
          {renderInline(text)}
        </h4>
      );
      i++;
      continue;
    }

    if (trimmed.startsWith('### ')) {
      const text = trimmed.slice(4).trim();
      const anchorId = text.toLowerCase().replace(/[^a-z0-9]+/g, '-');
      blocks.push(
        <h3
          key={`block-${i}`}
          id={`heading-${anchorId}`}
          className="text-[16px] sm:text-[17px] font-semibold text-slate-900 mt-6 mb-2.5 tracking-tight scroll-mt-24"
        >
          {renderInline(text)}
        </h3>
      );
      i++;
      continue;
    }

    if (trimmed.startsWith('## ')) {
      const text = trimmed.slice(3).trim();
      const anchorId = text.toLowerCase().replace(/[^a-z0-9]+/g, '-');
      blocks.push(
        <h2
          key={`block-${i}`}
          id={`heading-${anchorId}`}
          className="text-[19px] sm:text-[20px] font-semibold text-slate-900 mt-8 mb-3.5 pb-1.5 border-b border-slate-200 tracking-tight scroll-mt-24"
        >
          {renderInline(text)}
        </h2>
      );
      i++;
      continue;
    }

    if (trimmed.startsWith('# ')) {
      const text = trimmed.slice(2).trim();
      blocks.push(
        <h1 key={`block-${i}`} className="text-[22px] sm:text-[24px] font-bold text-slate-900 mt-8 mb-4 tracking-tight">
          {renderInline(text)}
        </h1>
      );
      i++;
      continue;
    }

    // 5. Unordered List Items
    if (/^[-*]\s+/.test(trimmed)) {
      const listItems: string[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        listItems.push(lines[i].trim().replace(/^[-*]\s+/, ''));
        i++;
      }
      blocks.push(
        <ul key={`block-${i}`} className="my-3 space-y-1.5 list-none pl-1">
          {listItems.map((item, itemIdx) => (
            <li key={itemIdx} className="flex items-start text-[14px] sm:text-[15px] leading-relaxed text-slate-700">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-sky-500 mt-2 mr-3 shrink-0" />
              <div className="flex-1">{renderInline(item)}</div>
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // 6. Ordered List Items
    if (/^\d+\.\s+/.test(trimmed)) {
      const listItems: { num: string; text: string }[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        const itemMatch = lines[i].trim().match(/^(\d+)\.\s+(.*)$/);
        if (itemMatch) {
          listItems.push({ num: itemMatch[1], text: itemMatch[2] });
        }
        i++;
      }
      blocks.push(
        <ol key={`block-${i}`} className="my-3 space-y-1.5 list-none pl-1">
          {listItems.map((item, itemIdx) => (
            <li key={itemIdx} className="flex items-start text-[14px] sm:text-[15px] leading-relaxed text-slate-700">
              <span className="font-mono text-xs font-bold text-sky-700 bg-sky-50 px-1.5 py-0.5 rounded mr-2.5 mt-0.5 shrink-0 border border-sky-200">
                {item.num}
              </span>
              <div className="flex-1">{renderInline(item.text)}</div>
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // 7. Regular Paragraph (14-16px body scale)
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].trim().startsWith('```') &&
      !(lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) &&
      !lines[i].trim().startsWith('>') &&
      !lines[i].trim().startsWith('#') &&
      !/^[-*]\s+/.test(lines[i].trim()) &&
      !/^\d+\.\s+/.test(lines[i].trim())
    ) {
      paraLines.push(lines[i].trim());
      i++;
    }

    if (paraLines.length > 0) {
      blocks.push(
        <p key={`block-${i}`} className="my-3 text-[14px] sm:text-[15px] leading-relaxed text-slate-700 font-normal">
          {renderInline(paraLines.join(' '))}
        </p>
      );
    }
  }

  return <div className={`space-y-1 text-slate-800 ${className}`}>{blocks}</div>;
};
