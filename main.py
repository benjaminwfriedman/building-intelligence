import logging
import uvicorn
import os
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from models import QueryRequest, QueryResponse
from scene_graph_service import SceneGraphService
from database import db
from config import Config
from chat_service import chat_service, ChatMessage
from chat_models import ChatRequest, WebSocketMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
scene_service = SceneGraphService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        Config.validate()
        db.create_schema()
        logger.info("Application startup completed")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    db.close()
    logger.info("Application shutdown completed")

app = FastAPI(
    title="Engineering Scene Graph API",
    description="Extract scene graphs from engineering diagrams and query them with natural language",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Engineering Scene Graph API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/upload - Upload and process engineering diagrams",
            "query": "/query - Query scene graphs with natural language",
            "diagrams": "/diagrams - List all processed diagrams",
            "diagram": "/diagrams/{diagram_id} - Get diagram details",
            "health": "/health - System health check"
        }
    }

@app.post("/upload")
async def upload_diagram(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Read file content
        file_bytes = await file.read()
        
        # Validate file size
        if len(file_bytes) > Config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size: {Config.MAX_FILE_SIZE} bytes"
            )
        
        # Process file and create scene graph
        scene_graph = scene_service.create_scene_graph_from_file(
            file.filename, 
            file_bytes
        )
        
        return {
            "diagram_id": scene_graph.diagram_id,
            "title": scene_graph.title,
            "components_count": len(scene_graph.nodes),
            "relationships_count": len(scene_graph.relationships),
            "metadata": scene_graph.metadata,
            "message": "Scene graph created successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# New WebSocket endpoint for streaming chat
@app.websocket("/ws/chat/{diagram_id}")
async def websocket_chat(websocket: WebSocket, diagram_id: str):
    await websocket.accept()
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            # Save user message to chat history
            user_message = ChatMessage(
                id=chat_service.create_message_id(),
                diagram_id=diagram_id,
                role="user",
                content=data,
                timestamp=datetime.now()
            )
            chat_service.save_message(user_message)
            
            # Send status message
            await websocket.send_text(WebSocketMessage(
                type="status",
                content="Processing your question..."
            ).model_dump_json())
            
            try:
                # Get response from scene graph service
                result = scene_service.query_scene_graphs(data, diagram_id)
                
                # Save assistant message
                assistant_message = ChatMessage(
                    id=chat_service.create_message_id(),
                    diagram_id=diagram_id,
                    role="assistant", 
                    content=result['answer'],
                    timestamp=datetime.now(),
                    confidence=result['confidence']
                )
                chat_service.save_message(assistant_message)
                
                # Send the response
                await websocket.send_text(WebSocketMessage(
                    type="message",
                    content=result['answer'],
                    message_id=assistant_message.id
                ).model_dump_json())
                
            except Exception as e:
                logger.error(f"Query processing error: {e}")
                await websocket.send_text(WebSocketMessage(
                    type="error",
                    content="Sorry, I encountered an error processing your question."
                ).model_dump_json())
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for diagram {diagram_id}")

# Chat history endpoints
@app.get("/api/chat/history/{diagram_id}")
async def get_chat_history(diagram_id: str):
    try:
        messages = chat_service.get_chat_history(diagram_id)
        return {
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "confidence": msg.confidence
                }
                for msg in messages
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/chat/clear/{diagram_id}")
async def clear_chat_history(diagram_id: str):
    try:
        success = chat_service.clear_chat_history(diagram_id)
        if success:
            return {"message": "Chat history cleared"}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear chat history")
    except Exception as e:
        logger.error(f"Failed to clear chat history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Serve diagram images
@app.get("/diagrams/{diagram_id}/image")
async def get_diagram_image(diagram_id: str):
    try:
        # For now, return the SimpleRiser.png - in production this would be stored per diagram
        image_path = "SimpleRiser.png"
        if os.path.exists(image_path):
            return FileResponse(image_path, media_type="image/png")
        else:
            raise HTTPException(status_code=404, detail="Diagram image not found")
    except Exception as e:
        logger.error(f"Failed to serve diagram image: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Get components for diagram overlay
@app.get("/api/diagrams/{diagram_id}/components")
async def get_diagram_components(diagram_id: str):
    try:
        # Get the complete scene graph data
        graph_data = scene_service._get_complete_scene_graph(diagram_id)
        if not graph_data:
            raise HTTPException(status_code=404, detail="Diagram not found")
        
        # Extract and format component data for frontend
        components = []
        for i, component in enumerate(graph_data['components']):
            components.append({
                'id': component['id'],
                'badge_number': i + 1,  # 1-indexed badges
                'name': component['name'],
                'type': component['type'],
                'position': {
                    'x': component.get('position_x', 0) or 0,
                    'y': component.get('position_y', 0) or 0
                },
                'properties': {
                    'material': component.get('material', ''),
                    'diameter': component.get('diameter', ''),
                    'flow_direction': component.get('flow_direction', '')
                }
            })
        
        return {
            'diagram_id': diagram_id,
            'components': components,
            'total_components': len(components)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get diagram components: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/query", response_model=QueryResponse)
async def query_diagrams(request: QueryRequest):
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        result = scene_service.query_scene_graphs(
            request.question,
            request.graph_id
        )
        
        return QueryResponse(
            answer=result['answer'],
            confidence=result['confidence']
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/diagrams")
async def list_diagrams():
    try:
        diagrams = scene_service.list_all_diagrams()
        return {
            "diagrams": diagrams,
            "count": len(diagrams)
        }
    except Exception as e:
        logger.error(f"Failed to list diagrams: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/diagrams/{diagram_id}")
async def get_diagram(diagram_id: str):
    try:
        diagram_info = scene_service.get_diagram_summary(diagram_id)
        if not diagram_info:
            raise HTTPException(status_code=404, detail="Diagram not found")
        
        return diagram_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get diagram: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    try:
        # Check database connection
        db_healthy = db.health_check()
        
        # Check OpenAI API (basic validation)
        openai_healthy = bool(Config.OPENAI_API_KEY)
        
        status = "healthy" if db_healthy and openai_healthy else "unhealthy"
        
        return {
            "status": status,
            "database": "connected" if db_healthy else "disconnected",
            "openai": "configured" if openai_healthy else "not_configured",
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )