import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { ProjectView } from './pages/ProjectView';
import { SettingsPage } from './pages/SettingsPage';
import { AuthPage } from './pages/AuthPage';

const AppContent: React.FC = () => {
  const { user, loading } = useAuth();
  const [currentView, setCurrentView] = useState<'dashboard' | 'project' | 'settings'>('dashboard');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

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
    setSelectedProjectId(id);
    setCurrentView('project');
  };

  const handleBackToDashboard = () => {
    setSelectedProjectId(null);
    setCurrentView('dashboard');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar
        currentView={currentView}
        onNavigate={(view) => {
          if (view === 'dashboard') handleBackToDashboard();
          if (view === 'settings') setCurrentView('settings');
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
