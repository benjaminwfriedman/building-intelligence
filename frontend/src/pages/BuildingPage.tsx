import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';

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

interface BuildingPageProps {
  building: Building;
  onBack: () => void;
  onSelectDrawing: (drawing: Drawing) => void;
}

export default function BuildingPage({ building, onBack, onSelectDrawing }: BuildingPageProps) {
  const [drawings, setDrawings] = useState<Drawing[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');

  const { token } = useAuth();

  useEffect(() => {
    fetchDrawings();
  }, [building.id]);

  const fetchDrawings = async () => {
    try {
      // Note: We'll need to add this endpoint to the backend
      const response = await fetch(`/buildings/${building.id}/drawings`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const drawingsData = await response.json();
        setDrawings(drawingsData);
      } else {
        console.error('Failed to fetch drawings');
      }
    } catch (error) {
      console.error('Error fetching drawings:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadProgress('Uploading file...');

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('building_id', building.id.toString());

      const response = await fetch('/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (response.ok) {
        setUploadProgress('Processing diagram with GPT-5...');
        const result = await response.json();
        
        // Create drawing record
        const newDrawing: Drawing = {
          id: Date.now(), // Temporary ID
          filename: file.name,
          title: result.title,
          scene_graph_id: result.diagram_id,
          created_at: new Date().toISOString(),
        };
        
        setDrawings(prev => [...prev, newDrawing]);
        setUploadProgress('');
        
        // Auto-select the new drawing
        onSelectDrawing(newDrawing);
      } else {
        setUploadProgress('Upload failed');
        setTimeout(() => setUploadProgress(''), 3000);
      }
    } catch (error) {
      console.error('Upload error:', error);
      setUploadProgress('Upload failed');
      setTimeout(() => setUploadProgress(''), 3000);
    } finally {
      setIsUploading(false);
      // Reset file input
      e.target.value = '';
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div className="flex items-center space-x-4">
              <button
                onClick={onBack}
                className="text-gray-600 hover:text-gray-900 p-1"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{building.name}</h1>
                <p className="text-gray-600">
                  {building.address && `${building.address} • `}
                  {building.drawing_count} drawings
                </p>
              </div>
            </div>
            
            {/* Upload Button */}
            <div className="relative">
              <input
                type="file"
                id="file-upload"
                accept=".png,.jpg,.jpeg,.pdf"
                onChange={handleFileUpload}
                className="hidden"
                disabled={isUploading}
              />
              <label
                htmlFor="file-upload"
                className={`bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium cursor-pointer inline-flex items-center ${
                  isUploading ? 'opacity-50 cursor-not-allowed' : ''
                }`}
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Upload Drawing
              </label>
            </div>
          </div>
          
          {/* Upload Progress */}
          {uploadProgress && (
            <div className="pb-4">
              <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded">
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                  {uploadProgress}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Drawings Grid */}
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 sm:px-0">
          {isLoading ? (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            </div>
          ) : drawings.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-200 rounded-lg mx-auto mb-4 flex items-center justify-center">
                <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No drawings yet</h3>
              <p className="text-gray-500 mb-4">Upload engineering diagrams to start analyzing them</p>
              <label
                htmlFor="file-upload"
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium cursor-pointer inline-flex items-center"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Upload Your First Drawing
              </label>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {drawings.map((drawing) => (
                <div
                  key={drawing.id}
                  className="bg-white rounded-lg shadow hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => onSelectDrawing(drawing)}
                >
                  <div className="p-6">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-semibold text-gray-900 truncate">
                        {drawing.title || drawing.filename}
                      </h3>
                      <span className="bg-green-100 text-green-800 text-xs font-medium px-2.5 py-0.5 rounded">
                        Processed
                      </span>
                    </div>
                    
                    <p className="text-sm text-gray-600 mb-2">
                      {drawing.filename}
                    </p>
                    
                    <p className="text-xs text-gray-400">
                      Uploaded {new Date(drawing.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  
                  <div className="bg-gray-50 px-6 py-3 rounded-b-lg">
                    <div className="text-sm text-blue-600 font-medium">
                      Click to analyze →
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