import { useState, useRef, useEffect } from 'react';

interface Diagram {
  diagram_id: string;
  title: string;
  component_count: number;
}

interface Component {
  id: string;
  badge_number: number;
  name: string;
  type: string;
  position: { x: number; y: number };
  properties: {
    material: string;
    diameter: string;
    flow_direction: string;
  };
}

interface DiagramViewerProps {
  diagram: Diagram | null;
  highlightedComponents?: string[];
  onComponentClick?: (componentId: string) => void;
}

export default function DiagramViewer({ diagram, highlightedComponents = [], onComponentClick }: DiagramViewerProps) {
  const [zoom, setZoom] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [lastMousePos, setLastMousePos] = useState({ x: 0, y: 0 });
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const imageRef = useRef<HTMLImageElement>(null);


  if (!diagram) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-16 h-16 bg-gray-200 rounded-lg mx-auto mb-4 flex items-center justify-center">
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <p className="text-gray-500">No diagram selected</p>
          <p className="text-sm text-gray-400 mt-1">Upload a diagram to get started</p>
        </div>
      </div>
    );
  }

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY * -0.001;
    const newZoom = Math.max(0.1, Math.min(5, zoom + delta));
    setZoom(newZoom);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setLastMousePos({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    
    const deltaX = e.clientX - lastMousePos.x;
    const deltaY = e.clientY - lastMousePos.y;
    
    setPosition(prev => ({
      x: prev.x + deltaX,
      y: prev.y + deltaY
    }));
    
    setLastMousePos({ x: e.clientX, y: e.clientY });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const zoomIn = () => setZoom(prev => Math.min(5, prev * 1.2));
  const zoomOut = () => setZoom(prev => Math.max(0.1, prev / 1.2));
  const resetView = () => {
    setZoom(1);
    setPosition({ x: 0, y: 0 });
  };

  return (
    <div className="h-full bg-white relative">
      {/* Diagram Header */}
      <div className="p-4 border-b bg-gray-50">
        <h3 className="font-medium text-gray-900 truncate">{diagram.title}</h3>
        <p className="text-sm text-gray-500 mt-1">{diagram.component_count} components</p>
      </div>

      {/* Diagram Image with Manual Zoom/Pan */}
      <div 
        className="h-full overflow-hidden cursor-grab active:cursor-grabbing"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{ height: 'calc(100% - 80px)' }}
      >
        <div 
          className="flex items-center justify-center h-full transition-transform duration-75 relative"
          style={{
            transform: `translate(${position.x}px, ${position.y}px) scale(${zoom})`,
            transformOrigin: 'center center'
          }}
        >
          <img
            ref={imageRef}
            src={`http://localhost:8000/diagrams/${diagram.diagram_id}/image`}
            alt={diagram.title}
            className="max-w-none shadow-lg border select-none"
            draggable={false}
            onLoad={(e) => {
              setImageLoaded(true);
              const img = e.currentTarget;
              setImageDimensions({ width: img.naturalWidth, height: img.naturalHeight });
            }}
            onError={(e) => {
              console.error('Failed to load diagram image');
              e.currentTarget.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJzYW5zLXNlcmlmIiBmb250LXNpemU9IjE0IiBmaWxsPSIjNmI3MjgwIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iMC4zNWVtIj5JbWFnZSBub3QgZm91bmQ8L3RleHQ+PC9zdmc+';
            }}
          />

        </div>
      </div>

      {/* Zoom Controls */}
      <div className="absolute top-20 right-4 bg-white border rounded-lg shadow-sm p-2 space-y-2">
        <button
          onClick={zoomIn}
          className="block w-8 h-8 bg-white hover:bg-gray-50 border rounded text-sm font-mono"
          title="Zoom In"
        >
          +
        </button>
        <button
          onClick={zoomOut}
          className="block w-8 h-8 bg-white hover:bg-gray-50 border rounded text-sm font-mono"
          title="Zoom Out"
        >
          −
        </button>
        <button
          onClick={resetView}
          className="block w-8 h-8 bg-white hover:bg-gray-50 border rounded text-xs"
          title="Reset View"
        >
          ⌂
        </button>
      </div>

      {/* Zoom Level Indicator */}
      <div className="absolute bottom-4 right-4 bg-black bg-opacity-75 text-white px-2 py-1 rounded text-xs">
        {Math.round(zoom * 100)}%
      </div>
    </div>
  );
}