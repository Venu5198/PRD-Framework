import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { SystemHealth } from '../types';
import { Cpu, ShieldCheck, HardDrive, CheckCircle2, AlertCircle, RefreshCw, ArrowLeft } from 'lucide-react';

export const SettingsPage: React.FC<{ onBack: () => void }> = ({ onBack }) => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [models, setModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const h = await api.getHealth();
      setHealth(h);
      setSelectedModel(h.ai_engine.default_model);

      const m = await api.getModels();
      setModels(m.available_models);
    } catch (_) {}
    finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelectModel = async () => {
    if (!selectedModel) return;
    setSaving(true);
    try {
      await api.selectModel(selectedModel);
      await loadData();
      alert(`Model changed to: ${selectedModel}`);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <button
        onClick={onBack}
        className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Projects</span>
      </button>

      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">System & AI Configuration</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Manage local Ollama model selection, offline fallbacks, and data privacy settings.
        </p>
      </div>

      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
        {/* Model Selection */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Cpu className="w-5 h-5 text-sky-600" />
              <h2 className="text-sm font-bold text-slate-900">Local AI Inference Model</h2>
            </div>
            <button
              onClick={loadData}
              className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 font-medium"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh Models</span>
            </button>
          </div>

          <p className="text-xs text-slate-600">
            Select which locally hosted model Ollama uses for pipeline stages (Input Analysis, Clarifications,
            Requirement Engineering, and PRD Generation).
          </p>

          <div className="flex flex-col sm:flex-row gap-2">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full min-w-0 px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-sky-500 truncate"
            >
              <option value="llama3.2">llama3.2 (Recommended: 3B Fast & Efficient)</option>
              <option value="mistral">mistral (7B Standard Architecture)</option>
              <option value="llama3">llama3 (8B Comprehensive)</option>
              <option value="qwen2.5-coder">qwen2.5-coder (Technical Requirements)</option>
              {models.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name}
                </option>
              ))}
            </select>
            <button
              onClick={handleSelectModel}
              disabled={saving}
              className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition disabled:opacity-50 shrink-0"
            >
              {saving ? 'Updating...' : 'Set Active Model'}
            </button>
          </div>
        </div>

        {/* Local Sovereignty Guarantee */}
        <div className="p-4 bg-emerald-50/70 border border-emerald-200 rounded-xl space-y-2">
          <div className="flex items-center space-x-2 text-xs font-bold text-emerald-900">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Local Sovereignty & Offline Guarantee (NFR-001)</span>
          </div>
          <p className="text-xs text-emerald-800 leading-relaxed">
            The platform executes exclusively inside your local environment. Zero telemetry or user prompts
            are forwarded to third-party cloud servers or proprietary AI APIs.
          </p>
        </div>

        {/* Runtime Diagnostics */}
        <div className="pt-4 border-t border-slate-100 space-y-3">
          <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Runtime Diagnostics</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
              <span className="text-slate-600 font-medium">Ollama Daemon:</span>
              <span className="font-semibold text-slate-900 flex items-center gap-1">
                {health?.ai_engine.available ? (
                  <span className="text-emerald-600 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Reachable (11434)
                  </span>
                ) : (
                  <span className="text-amber-600 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" /> Inactive (Offline Fallback)
                  </span>
                )}
              </span>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
              <span className="text-slate-600 font-medium">Database Persistence:</span>
              <span className="font-semibold text-slate-900">
                {health?.database.is_in_memory_mock ? 'In-Memory AsyncClient' : 'Local MongoDB (27017)'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

