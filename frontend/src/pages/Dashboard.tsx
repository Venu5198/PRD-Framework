import React, { useEffect, useState } from 'react';
import { Project, SystemHealth } from '../types';
import { api } from '../api/client';
import { FolderPlus, FileText, ChevronRight, HardDrive, Cpu, Plus, Sparkles } from 'lucide-react';

interface DashboardProps {
  onSelectProject: (projectId: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onSelectProject }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newDomain, setNewDomain] = useState('General Software');
  const [creating, setCreating] = useState(false);
  const [health, setHealth] = useState<SystemHealth | null>(null);

  const loadProjects = async () => {
    try {
      const list = await api.getProjects();
      setProjects(list);
      const h = await api.getHealth();
      setHealth(h);
    } catch (_) {}
    finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      const p = await api.createProject(newTitle, newDesc, newDomain);
      setShowModal(false);
      setNewTitle('');
      setNewDesc('');
      onSelectProject(p.id);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Welcome / Hero Banner */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 rounded-2xl p-8 text-white shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6 border border-slate-700">
        <div className="space-y-2 max-w-2xl">
          <div className="inline-flex items-center space-x-2 text-xs font-semibold px-2.5 py-1 bg-sky-950 text-sky-400 border border-sky-800 rounded-full">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI-Powered Requirements Engineering</span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight">Idea in. Professional PRD out.</h1>
          <p className="text-slate-300 text-sm leading-relaxed">
            Transform raw concepts, problem statements, and course assignments into 27-section
            traceable PRD documents. Runs 100% locally with zero cloud dependencies.
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center space-x-2 px-5 py-3 bg-sky-500 hover:bg-sky-400 text-white font-semibold rounded-xl shadow-lg transition"
        >
          <Plus className="w-5 h-5" />
          <span>New PRD Project</span>
        </button>
      </div>

      {/* System Status Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="p-3 bg-sky-50 text-sky-600 rounded-lg">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-slate-500 font-medium uppercase tracking-wider">Active Projects</div>
            <div className="text-2xl font-bold text-slate-900">{projects.length}</div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="p-3 bg-emerald-50 text-emerald-600 rounded-lg">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-slate-500 font-medium uppercase tracking-wider">AI Provider</div>
            <div className="text-sm font-bold text-slate-800 truncate">
              {health?.ai_engine.default_model || 'Local Model'}
            </div>
            <div className="text-[11px] text-emerald-600 font-medium">
              {health?.ai_engine.available ? 'Ollama Daemon Active' : 'Offline Engine Fallback'}
            </div>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="p-3 bg-indigo-50 text-indigo-600 rounded-lg">
            <HardDrive className="w-6 h-6" />
          </div>
          <div>
            <div className="text-xs text-slate-500 font-medium uppercase tracking-wider">Storage & Database</div>
            <div className="text-sm font-bold text-slate-800">
              {health?.database.is_in_memory_mock ? 'In-Memory Engine' : 'Local MongoDB Community'}
            </div>
            <div className="text-[11px] text-slate-500">Zero External Telemetry</div>
          </div>
        </div>
      </div>

      {/* Project Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">Your PRD Projects</h2>
          <span className="text-xs text-slate-500">{projects.length} Total Projects</span>
        </div>

        {loading ? (
          <div className="py-16 text-center text-slate-400 text-sm">Loading projects...</div>
        ) : projects.length === 0 ? (
          <div className="bg-white border-2 border-dashed border-slate-300 rounded-2xl p-12 text-center space-y-4">
            <div className="w-12 h-12 bg-sky-50 text-sky-500 rounded-full flex items-center justify-center mx-auto">
              <FolderPlus className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900">No projects yet</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
                Start by creating your first product requirements project and submitting an initial idea or assignment.
              </p>
            </div>
            <button
              onClick={() => setShowModal(true)}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-900 text-white text-xs font-semibold rounded-lg hover:bg-slate-800 transition"
            >
              <Plus className="w-4 h-4" />
              <span>Create Project</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {projects.map((p) => (
              <div
                key={p.id}
                onClick={() => onSelectProject(p.id)}
                className="bg-white p-6 rounded-xl border border-slate-200 hover:border-sky-300 hover:shadow-md transition cursor-pointer flex flex-col justify-between space-y-4 group"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold text-sky-600 bg-sky-50 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                      {p.target_domain || 'General Software'}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      {new Date(p.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-slate-900 group-hover:text-sky-600 transition">
                    {p.title}
                  </h3>
                  <p className="text-xs text-slate-500 line-clamp-2">
                    {p.description || 'No project description provided.'}
                  </p>
                </div>

                <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
                  <span className="font-medium text-slate-500">
                    {p.active_prd_id ? 'PRD Generated' : 'Idea Stage'}
                  </span>
                  <div className="flex items-center space-x-1 text-sky-600 font-semibold group-hover:translate-x-0.5 transition">
                    <span>Open Project</span>
                    <ChevronRight className="w-4 h-4" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full p-6 border border-slate-200 space-y-4">
            <h3 className="text-lg font-bold text-slate-900">Create New PRD Project</h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Project Name *</label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. NextGen Micro-SaaS Platform"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Target Domain / Category</label>
                <select
                  value={newDomain}
                  onChange={(e) => setNewDomain(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-sky-500 bg-white"
                >
                  <option value="General Software">General Software</option>
                  <option value="Developer Tools & Infrastructure">Developer Tools & Infrastructure</option>
                  <option value="AI & Machine Learning">AI & Machine Learning</option>
                  <option value="Productivity & Workflow Automation">Productivity & Workflow Automation</option>
                  <option value="Fintech & E-commerce">Fintech & E-commerce</option>
                  <option value="Healthcare & Privacy Systems">Healthcare & Privacy Systems</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Brief Description (Optional)</label>
                <textarea
                  rows={3}
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Optional context about the problem or objective..."
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-medium hover:bg-slate-800 transition disabled:opacity-50"
                >
                  {creating ? 'Creating...' : 'Create & Proceed'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

