import { useState, useEffect } from 'react'
import DiagramViewer from './components/DiagramViewer'
import ChatInterface from './components/ChatInterface'

interface Diagram {
  diagram_id: string;
  title: string;
  component_count: number;
}

function App() {
  const [diagrams, setDiagrams] = useState<Diagram[]>([]);
  const [selectedDiagram, setSelectedDiagram] = useState<Diagram | null>(null);
  const [highlightedComponents, setHighlightedComponents] = useState<string[]>([]);

  useEffect(() => {
    // Fetch available diagrams from the backend
    fetch('http://localhost:8000/diagrams')
      .then(res => res.json())
      .then(data => {
        setDiagrams(data.diagrams);
        if (data.diagrams.length > 0) {
          setSelectedDiagram(data.diagrams[0]);
        }
      })
      .catch(err => console.error('Failed to fetch diagrams:', err));
  }, []);

  return (
    <div className="h-screen bg-gray-100 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-gray-900">
            Engineering Scene Graph Assistant
          </h1>
          {diagrams.length > 1 && (
            <select 
              className="border rounded px-3 py-1"
              value={selectedDiagram?.diagram_id || ''}
              onChange={(e) => {
                const diagram = diagrams.find(d => d.diagram_id === e.target.value);
                if (diagram) setSelectedDiagram(diagram);
              }}
            >
              {diagrams.map(diagram => (
                <option key={diagram.diagram_id} value={diagram.diagram_id}>
                  {diagram.title}
                </option>
              ))}
            </select>
          )}
        </div>
        {selectedDiagram && (
          <p className="text-sm text-gray-600 mt-1">
            {selectedDiagram.title} • {selectedDiagram.component_count} components
          </p>
        )}
      </div>

      {/* Main Content - Split Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Diagram */}
        <div className="w-1/2 bg-white border-r">
          <DiagramViewer 
            diagram={selectedDiagram}
            highlightedComponents={highlightedComponents}
            onComponentClick={(componentId) => {
              // Toggle highlighting when component badge is clicked
              setHighlightedComponents(prev => 
                prev.includes(componentId) 
                  ? prev.filter(id => id !== componentId)
                  : [componentId]
              );
            }}
          />
        </div>
        
        {/* Right Panel - Chat */}
        <div className="w-1/2 bg-gray-50">
          <ChatInterface 
            diagram={selectedDiagram}
            highlightedComponents={highlightedComponents}
            onComponentHighlight={(componentIds) => {
              setHighlightedComponents(componentIds);
            }}
          />
        </div>
      </div>
    </div>
  )
}

export default App
