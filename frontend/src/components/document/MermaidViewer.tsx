import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { Copy, Check, Eye, EyeOff, Code, AlertCircle } from 'lucide-react';

interface MermaidViewerProps {
  chart: string;
}

let mermaidIdCounter = 0;

export const MermaidViewer: React.FC<MermaidViewerProps> = ({ chart }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgHtml, setSvgHtml] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [showRaw, setShowRaw] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const renderDiagram = async () => {
      if (!chart || !chart.trim()) return;

      try {
        mermaid.initialize({
          startOnLoad: false,
          theme: 'neutral',
          securityLevel: 'loose',
          fontFamily: 'Inter, system-ui, sans-serif',
        });

        const id = `mermaid-chart-${Date.now()}-${mermaidIdCounter++}`;
        const cleanChart = chart.trim();
        const { svg } = await mermaid.render(id, cleanChart);
        
        if (isMounted) {
          setSvgHtml(svg);
          setError(null);
        }
      } catch (err: any) {
        if (isMounted) {
          console.warn('Mermaid rendering failed, using fallback:', err);
          setError(err?.message || 'Diagram syntax parsing error');
        }
      }
    };

    renderDiagram();
    return () => {
      isMounted = false;
    };
  }, [chart]);

  const handleCopy = () => {
    navigator.clipboard.writeText(chart);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-6 rounded-xl border border-slate-200 bg-slate-50/60 overflow-hidden shadow-xs">
      {/* Diagram Header / Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-100/80 border-b border-slate-200 text-xs text-slate-600">
        <div className="flex items-center space-x-2 font-medium">
          <Code className="w-3.5 h-3.5 text-slate-500" />
          <span className="font-semibold text-slate-700">Architecture & Interaction Flow</span>
          <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-200/70 text-slate-600">
            Mermaid Diagram
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowRaw(!showRaw)}
            className="inline-flex items-center space-x-1 px-2 py-1 text-slate-600 hover:text-slate-900 hover:bg-slate-200/60 rounded transition"
            title="Toggle Raw Code"
          >
            {showRaw ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            <span>{showRaw ? 'View Diagram' : 'View Code'}</span>
          </button>
          <button
            onClick={handleCopy}
            className="inline-flex items-center space-x-1 px-2 py-1 text-slate-600 hover:text-slate-900 hover:bg-slate-200/60 rounded transition"
            title="Copy Diagram Code"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>

      {/* Render Area */}
      <div className="p-4 sm:p-6 overflow-x-auto bg-white flex justify-center">
        {showRaw ? (
          <pre className="w-full text-xs font-mono p-4 bg-slate-900 text-slate-100 rounded-lg overflow-x-auto leading-relaxed">
            {chart}
          </pre>
        ) : error ? (
          <div className="w-full space-y-3 py-4">
            <div className="flex items-start space-x-3 p-3.5 bg-amber-50/80 border border-amber-200 rounded-lg text-amber-900 text-xs">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Visual rendering fallback active</p>
                <p className="text-amber-700 mt-0.5">
                  The diagram definition is displayed below as structured technical specification.
                </p>
              </div>
            </div>
            <pre className="text-xs font-mono p-4 bg-slate-900 text-slate-100 rounded-lg overflow-x-auto leading-relaxed">
              {chart}
            </pre>
          </div>
        ) : svgHtml ? (
          <div
            ref={containerRef}
            className="w-full flex justify-center overflow-x-auto [&_svg]:max-w-full [&_svg]:h-auto"
            dangerouslySetInnerHTML={{ __html: svgHtml }}
          />
        ) : (
          <div className="py-8 text-center text-xs text-slate-400 animate-pulse">
            Rendering interactive diagram...
          </div>
        )}
      </div>
    </div>
  );
};
