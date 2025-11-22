import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

interface Building {
  id: number;
  name: string;
  address?: string;
  description?: string;
  drawing_count: number;
  created_at: string;
}

interface DashboardProps {
  onSelectBuilding: (building: Building) => void;
}

export default function Dashboard({ onSelectBuilding }: DashboardProps) {
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newBuilding, setNewBuilding] = useState({
    name: '',
    address: '',
    description: ''
  });
  const [isCreating, setIsCreating] = useState(false);

  const { user, logout, token } = useAuth();

  useEffect(() => {
    fetchBuildings();
  }, []);

  const fetchBuildings = async () => {
    try {
      const response = await fetch('/buildings', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const buildingsData = await response.json();
        setBuildings(buildingsData);
      } else {
        console.error('Failed to fetch buildings');
      }
    } catch (error) {
      console.error('Error fetching buildings:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const createBuilding = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreating(true);

    try {
      const response = await fetch('/buildings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(newBuilding),
      });

      if (response.ok) {
        const building = await response.json();
        setBuildings(prev => [...prev, building]);
        setNewBuilding({ name: '', address: '', description: '' });
        setShowCreateForm(false);
      } else {
        console.error('Failed to create building');
      }
    } catch (error) {
      console.error('Error creating building:', error);
    } finally {
      setIsCreating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Engineering Scene Graph</h1>
              <p className="text-gray-600">Welcome back, {user?.username}</p>
            </div>
            <button
              onClick={logout}
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md text-sm font-medium"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-semibold text-gray-900">Your Buildings</h2>
            <button
              onClick={() => setShowCreateForm(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
            >
              Add Building
            </button>
          </div>

          {/* Create Building Form */}
          {showCreateForm && (
            <div className="bg-white p-6 rounded-lg shadow mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Create New Building</h3>
              <form onSubmit={createBuilding} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Building Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={newBuilding.name}
                    onChange={(e) => setNewBuilding(prev => ({ ...prev, name: e.target.value }))}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Main Office Building"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Address
                  </label>
                  <input
                    type="text"
                    value={newBuilding.address}
                    onChange={(e) => setNewBuilding(prev => ({ ...prev, address: e.target.value }))}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="123 Main Street, City, State"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Description
                  </label>
                  <textarea
                    value={newBuilding.description}
                    onChange={(e) => setNewBuilding(prev => ({ ...prev, description: e.target.value }))}
                    rows={3}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Brief description of the building..."
                  />
                </div>
                <div className="flex space-x-3">
                  <button
                    type="submit"
                    disabled={isCreating}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50"
                  >
                    {isCreating ? 'Creating...' : 'Create Building'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowCreateForm(false)}
                    className="bg-gray-300 hover:bg-gray-400 text-gray-700 px-4 py-2 rounded-md text-sm font-medium"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Buildings Grid */}
          {buildings.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-200 rounded-lg mx-auto mb-4 flex items-center justify-center">
                <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-2m-2 0H5m0 0H3m2 0h2m14 0v-2a2 2 0 00-2-2H9a2 2 0 00-2 2v2z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No buildings yet</h3>
              <p className="text-gray-500 mb-4">Create your first building to start uploading engineering diagrams</p>
              <button
                onClick={() => setShowCreateForm(true)}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                Create Your First Building
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {buildings.map((building) => (
                <div
                  key={building.id}
                  className="bg-white rounded-lg shadow hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => onSelectBuilding(building)}
                >
                  <div className="p-6">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-semibold text-gray-900 truncate">
                        {building.name}
                      </h3>
                      <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded">
                        {building.drawing_count} drawings
                      </span>
                    </div>
                    
                    {building.address && (
                      <p className="text-sm text-gray-600 mb-2">{building.address}</p>
                    )}
                    
                    {building.description && (
                      <p className="text-sm text-gray-500 mb-3 line-clamp-2">{building.description}</p>
                    )}
                    
                    <p className="text-xs text-gray-400">
                      Created {new Date(building.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  
                  <div className="bg-gray-50 px-6 py-3 rounded-b-lg">
                    <div className="text-sm text-blue-600 font-medium">
                      Click to view drawings →
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}