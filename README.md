# Engineering Scene Graph System

A full-stack system that extracts scene graphs from engineering diagrams using GPT-5.1 and provides an interactive web interface for natural language querying.

## 🌟 Features

### Backend
- **Document Processing**: Upload PDF or image files of engineering diagrams
- **Scene Graph Extraction**: Use GPT-5.1 to analyze diagrams and extract components, relationships, and properties
- **Graph Storage**: Store scene graphs in Neo4j Aura with optimized schema
- **Natural Language Querying**: Ask questions about diagrams in plain English using full graph context
- **WebSocket Streaming**: Real-time chat interface with streaming responses
- **Chat History**: Persistent conversation history with SQLite

### Frontend
- **Split-Screen Interface**: Diagram on left, chat on right
- **Interactive Diagram**: Zoom, pan, and inspect engineering diagrams
- **Streaming Chat**: Real-time responses with markdown formatting
- **Example Questions**: Quick-start prompts for users
- **Responsive Design**: Clean, modern interface with Tailwind CSS

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key with GPT-5.1 access
- Neo4j Aura database instance

### Installation

1. **Set up environment**:
```bash
cd building-intelligence
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

2. **Install frontend dependencies**:
```bash
cd frontend
npm install
cd ..
```

3. **Configure environment variables**:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
OPENAI_API_KEY=your_openai_api_key_here
NEO4J_URI=your_neo4j_aura_uri
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

### Running the Development Environment

**Easy way** (recommended):
```bash
./start_dev.sh
```

**Manual way**:
```bash
# Terminal 1 - Backend
source .venv/bin/activate
python main.py

# Terminal 2 - Frontend  
cd frontend
npm run dev
```

Visit `http://localhost:5173` to use the web interface!

## 💡 Usage

### Web Interface
1. Open `http://localhost:5173`
2. Your SimpleRiser.png diagram will load automatically
3. Start chatting! Try questions like:
   - "What materials are used in this plumbing system?"
   - "If the left vertical stack gets clogged, what would be impacted?"
   - "How many fixtures are on each floor?"
   - "What are the pipe diameters in this system?"

### API Usage

**Upload New Diagram**:
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_diagram.png"
```

**Query via REST API**:
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What types of pipes are shown?"}'
```

## 🏗️ Architecture

### Backend Stack
- **FastAPI**: Web framework with WebSocket support
- **GPT-5.1**: Advanced diagram analysis and scene graph extraction
- **GPT-4o-mini**: Natural language understanding with full graph context
- **Neo4j Aura**: Graph database for scene graph storage
- **SQLite**: Chat history persistence
- **PyMuPDF & Pillow**: Document and image processing

### Frontend Stack
- **React 18**: Modern UI framework
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Vite**: Fast development and building
- **react-markdown**: Rich text rendering
- **react-zoom-pan-pinch**: Interactive diagram viewing

### System Flow
1. **Upload**: User uploads engineering diagram
2. **Analysis**: GPT-5.1 extracts comprehensive scene graph
3. **Storage**: Scene graph stored in Neo4j with flattened properties
4. **Querying**: User asks questions via web chat interface
5. **Context Loading**: Complete scene graph loaded into GPT context
6. **Response**: GPT-4o-mini provides detailed technical answers

## 📁 Project Structure

```
building-intelligence/
├── backend/
│   ├── main.py              # FastAPI application with WebSocket
│   ├── scene_graph_service.py # Core business logic
│   ├── openai_client.py     # GPT integration
│   ├── database.py          # Neo4j interface
│   ├── chat_service.py      # Chat history management
│   ├── document_processor.py # File processing
│   ├── models.py            # Pydantic data models
│   └── config.py            # Configuration
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── DiagramViewer.tsx # Interactive diagram display
│   │   │   └── ChatInterface.tsx # Streaming chat interface
│   │   ├── App.tsx          # Main application layout
│   │   └── main.tsx         # Entry point
│   ├── package.json
│   └── vite.config.ts       # Development proxy setup
├── SimpleRiser.png          # Sample engineering diagram
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
└── start_dev.sh            # Development startup script
```

## 🧪 Testing

Run the QA test scripts to verify system functionality:

```bash
# Quick single question test
source .venv/bin/activate && python quick_test.py

# Comprehensive test suite
source .venv/bin/activate && python qa_test.py
```

## 🔧 Development

### Key Features Implemented
- ✅ Full-stack web interface with split-screen layout
- ✅ WebSocket streaming for real-time chat
- ✅ Interactive diagram viewing with zoom/pan
- ✅ Complete scene graph context for accurate answers
- ✅ Chat history persistence
- ✅ CORS configuration for development
- ✅ Markdown rendering for rich responses
- ✅ Error handling and graceful fallbacks

### Future Enhancements
- 🚧 Component highlighting in diagrams based on chat context
- 🚧 Multi-diagram support with dynamic switching  
- 🚧 Export chat conversations
- 🚧 Advanced diagram annotation tools
- 🚧 User authentication and project management

## 📊 Health Check

Check system status:
```bash
curl "http://localhost:8000/health"
```

The system is ready for immediate use with your SimpleRiser.png diagram and can be easily extended for production deployment!