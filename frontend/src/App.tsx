import { useState } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import BuildingPage from './pages/BuildingPage';
import ChatPage from './pages/ChatPage';

interface Building {
  id: number;
  name: string;
  address?: string;
  description?: string;
  drawing_count: number;
}

interface Drawing {
  id: number;
  filename: string;
  title?: string;
  scene_graph_id?: string;
  created_at: string;
}

type AppView = 'dashboard' | 'building' | 'chat';

function AppContent() {
  const [currentView, setCurrentView] = useState<AppView>('dashboard');
  const [selectedBuilding, setSelectedBuilding] = useState<Building | null>(null);
  const [selectedDrawing, setSelectedDrawing] = useState<Drawing | null>(null);

  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  const handleSelectBuilding = (building: Building) => {
    setSelectedBuilding(building);
    setCurrentView('building');
  };

  const handleSelectDrawing = (drawing: Drawing) => {
    setSelectedDrawing(drawing);
    setCurrentView('chat');
  };

  const handleBackToDashboard = () => {
    setSelectedBuilding(null);
    setSelectedDrawing(null);
    setCurrentView('dashboard');
  };

  const handleBackToBuilding = () => {
    setSelectedDrawing(null);
    setCurrentView('building');
  };

  // Render current view
  switch (currentView) {
    case 'dashboard':
      return <Dashboard onSelectBuilding={handleSelectBuilding} />;
    
    case 'building':
      return selectedBuilding ? (
        <BuildingPage
          building={selectedBuilding}
          onBack={handleBackToDashboard}
          onSelectDrawing={handleSelectDrawing}
        />
      ) : (
        <Dashboard onSelectBuilding={handleSelectBuilding} />
      );
    
    case 'chat':
      return selectedBuilding && selectedDrawing ? (
        <ChatPage
          building={selectedBuilding}
          drawing={selectedDrawing}
          onBack={handleBackToBuilding}
        />
      ) : (
        <Dashboard onSelectBuilding={handleSelectBuilding} />
      );
    
    default:
      return <Dashboard onSelectBuilding={handleSelectBuilding} />;
  }
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App
