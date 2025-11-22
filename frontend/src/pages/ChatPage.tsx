import DiagramViewer from '../components/DiagramViewer';
import ChatInterface from '../components/ChatInterface';

interface Building {
  id: number;
  name: string;
  address?: string;
}

interface Drawing {
  id: number;
  filename: string;
  title?: string;
  scene_graph_id?: string;
  created_at: string;
}

interface ChatPageProps {
  building: Building;
  drawing: Drawing;
  onBack: () => void;
}

// Convert Drawing to the Diagram interface expected by existing components
interface Diagram {
  diagram_id: string;
  title: string;
  component_count: number;
}

export default function ChatPage({ building, drawing, onBack }: ChatPageProps) {
  // Convert drawing to diagram format for existing components
  const diagram: Diagram = {
    diagram_id: drawing.scene_graph_id || '',
    title: drawing.title || drawing.filename,
    component_count: 25, // TODO: Get actual count from API
  };

  return (
    <div className="h-screen bg-gray-100 flex flex-col">
      {/* Enhanced Header with Building/Drawing Context */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
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
              <h1 className="text-xl font-semibold text-gray-900">
                Engineering Scene Graph Assistant
              </h1>
              <div className="flex items-center space-x-2 text-sm text-gray-600 mt-1">
                <span>{building.name}</span>
                <span>•</span>
                <span>{drawing.title || drawing.filename}</span>
                <span>•</span>
                <span>{diagram.component_count} components</span>
              </div>
            </div>
          </div>
          
          <div className="text-sm text-gray-500">
            Uploaded {new Date(drawing.created_at).toLocaleDateString()}
          </div>
        </div>
      </div>

      {/* Main Content - Split Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Diagram */}
        <div className="w-1/2 bg-white border-r">
          <DiagramViewer diagram={diagram} />
        </div>
        
        {/* Right Panel - Chat */}
        <div className="w-1/2 bg-gray-50">
          <ChatInterface diagram={diagram} />
        </div>
      </div>
    </div>
  );
}