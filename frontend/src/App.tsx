import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { ProjectView } from './pages/ProjectView';
import { SettingsPage } from './pages/SettingsPage';
import { AuthPage } from './pages/AuthPage';

const parseHashRoute = (): { view: 'dashboard' | 'project' | 'settings'; projectId: string | null } => {
  if (typeof window === 'undefined') return { view: 'dashboard', projectId: null };
  const hash = window.location.hash || '';
  if (hash === '#/settings') return { view: 'settings', projectId: null };
  if (hash.startsWith('#/project/')) {
    const id = hash.replace('#/project/', '').trim();
    if (id) return { view: 'project', projectId: id };
  }
  return { view: 'dashboard', projectId: null };
};

const AppContent: React.FC = () => {
  const { user, loading } = useAuth();
  const initialRoute = parseHashRoute();
  const [currentView, setCurrentView] = useState<'dashboard' | 'project' | 'settings'>(initialRoute.view);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(initialRoute.projectId);

  React.useEffect(() => {
    const handleHashChange = () => {
      const route = parseHashRoute();
      setCurrentView(route.view);
      setSelectedProjectId(route.projectId);
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center text-slate-400 text-sm">
        Initializing local session...
      </div>
    );
  }

  if (!user) {
    return <AuthPage />;
  }

  const handleOpenProject = (id: string) => {
    window.location.hash = `#/project/${id}`;
  };

  const handleBackToDashboard = () => {
    window.location.hash = '#/dashboard';
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar
        currentView={currentView}
        onNavigate={(view) => {
          if (view === 'dashboard') handleBackToDashboard();
          if (view === 'settings') window.location.hash = '#/settings';
        }}
      />

      <main className="flex-1 pb-16">
        {currentView === 'dashboard' && (
          <Dashboard onSelectProject={handleOpenProject} />
        )}
        {currentView === 'project' && selectedProjectId && (
          <ProjectView projectId={selectedProjectId} onBack={handleBackToDashboard} />
        )}
        {currentView === 'settings' && (
          <SettingsPage onBack={handleBackToDashboard} />
        )}
      </main>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;

