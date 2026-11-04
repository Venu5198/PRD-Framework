import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';
import { SystemHealth } from '../types';
import { FileText, Cpu, CheckCircle2, AlertCircle, LogOut, Settings as SettingsIcon } from 'lucide-react';

interface NavbarProps {
  currentView: string;
  onNavigate: (view: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentView, onNavigate }) => {
  const { user, logout } = useAuth();
  const [health, setHealth] = useState<SystemHealth | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const h = await api.getHealth();
        setHealth(h);
      } catch (_) {}
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => onNavigate('dashboard')}>
          <div className="bg-sky-500 p-2 rounded-lg text-white">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-lg tracking-tight">PRD Framework</span>
            <span className="ml-2 text-xs bg-sky-950 text-sky-400 border border-sky-800 px-2 py-0.5 rounded-full font-mono">
              LOCAL-FIRST
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {health && (
            <div className="hidden md:flex items-center space-x-2 text-xs bg-slate-800/80 px-3 py-1.5 rounded-md border border-slate-700">
              <Cpu className="w-4 h-4 text-sky-400" />
              <span>Model: <strong className="text-slate-200">{health.ai_engine.default_model}</strong></span>
              <span className="text-slate-500">|</span>
              {health.ai_engine.available ? (
                <span className="text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Ollama Active
                </span>
              ) : (
                <span className="text-amber-400 flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" /> Offline Mode
                </span>
              )}
            </div>
          )}

          <button
            onClick={() => onNavigate('settings')}
            className={`p-2 rounded-md hover:bg-slate-800 transition ${
              currentView === 'settings' ? 'text-sky-400 bg-slate-800' : 'text-slate-400'
            }`}
            title="Model & System Settings"
          >
            <SettingsIcon className="w-5 h-5" />
          </button>

          {user && (
            <div className="flex items-center space-x-3 pl-2 border-l border-slate-800">
              <div className="text-right hidden sm:block">
                <div className="text-xs font-semibold text-slate-200">{user.full_name || user.username}</div>
                <div className="text-[10px] text-slate-400 capitalize">{user.role}</div>
              </div>
              <button
                onClick={logout}
                className="p-1.5 text-slate-400 hover:text-rose-400 rounded-md transition"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
