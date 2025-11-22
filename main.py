import logging
import uvicorn
import os
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models import QueryRequest, QueryResponse
from scene_graph_service import SceneGraphService
from database import db
from config import Config
from chat_service import chat_service, ChatMessage
from chat_models import ChatRequest, WebSocketMessage
from auth_models import User, UserCreate, UserResponse, BuildingCreate, BuildingResponse, DrawingCreate, DrawingResponse, Token, LoginRequest
from auth_service import auth_service
from auth_database import auth_db
from blob_storage import blob_storage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
scene_service = SceneGraphService()
security = HTTPBearer()

# Dependency to get database session
def get_db() -> Session:
    return next(auth_db.get_session())

# Dependency to get current user from JWT token
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    user = auth_service.get_current_user_from_token(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        Config.validate()
        db.create_schema()  # Neo4j schema
        auth_db.create_tables()  # PostgreSQL/SQLite tables
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
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],  # Include Docker frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== AUTHENTICATION ENDPOINTS =====

@app.post("/auth/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        new_user = auth_service.create_user(db, user)
        return UserResponse.from_orm(new_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/auth/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token"""
    user = auth_service.authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=auth_service.config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse.from_orm(current_user)

# ===== BUILDING MANAGEMENT ENDPOINTS =====

@app.post("/buildings", response_model=BuildingResponse)
async def create_building(
    building: BuildingCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new building"""
    from auth_models import Building
    
    db_building = Building(
        name=building.name,
        address=building.address,
        description=building.description,
        owner_user_id=current_user.id
    )
    db.add(db_building)
    db.commit()
    db.refresh(db_building)
    
    response = BuildingResponse.from_orm(db_building)
    response.drawing_count = 0
    return response

@app.get("/buildings", response_model=List[BuildingResponse])
async def list_user_buildings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all buildings owned by current user"""
    from auth_models import Building, Drawing
    from sqlalchemy import func
    
    buildings = db.query(Building, func.count(Drawing.id).label('drawing_count'))\
                  .outerjoin(Drawing)\
                  .filter(Building.owner_user_id == current_user.id)\
                  .group_by(Building.id)\
                  .all()
    
    result = []
    for building, drawing_count in buildings:
        building_response = BuildingResponse.from_orm(building)
        building_response.drawing_count = drawing_count
        result.append(building_response)
    
    return result

@app.get("/buildings/{building_id}", response_model=BuildingResponse)
async def get_building(
    building_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific building (only if owned by current user)"""
    from auth_models import Building, Drawing
    from sqlalchemy import func
    
    building = db.query(Building)\
                 .filter(Building.id == building_id, Building.owner_user_id == current_user.id)\
                 .first()
    
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    
    drawing_count = db.query(func.count(Drawing.id))\
                      .filter(Drawing.building_id == building_id)\
                      .scalar()
    
    response = BuildingResponse.from_orm(building)
    response.drawing_count = drawing_count
    return response

# ===== DRAWING MANAGEMENT ENDPOINTS =====

@app.get("/buildings/{building_id}/drawings", response_model=List[DrawingResponse])
async def list_building_drawings(
    building_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all drawings in a building (only if user owns the building)"""
    from auth_models import Building, Drawing
    
    # Verify user owns the building
    building = db.query(Building)\
                 .filter(Building.id == building_id, Building.owner_user_id == current_user.id)\
                 .first()
    
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    
    # Get drawings for this building
    drawings = db.query(Drawing)\
                 .filter(Drawing.building_id == building_id)\
                 .order_by(Drawing.created_at.desc())\
                 .all()
    
    return [DrawingResponse.from_orm(drawing) for drawing in drawings]

@app.post("/upload")
async def upload_diagram(
    file: UploadFile = File(...),
    building_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and process engineering diagram"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Read file content
        file_bytes = await file.read()
        
        # Validate file size
        config = Config()
        if len(file_bytes) > config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size: {config.MAX_FILE_SIZE} bytes"
            )
        
        # Get the specified building or user's first building
        from auth_models import Building, Drawing
        
        if building_id:
            # Use specified building if provided
            user_building = db.query(Building)\
                              .filter(Building.id == building_id, Building.owner_user_id == current_user.id)\
                              .first()
            if not user_building:
                raise HTTPException(status_code=404, detail="Building not found or not owned by user")
        else:
            # Fallback to user's first building
            user_building = db.query(Building)\
                              .filter(Building.owner_user_id == current_user.id)\
                              .first()
            if not user_building:
                raise HTTPException(status_code=400, detail="No building found. Please create a building first.")
        
        # Save the uploaded image file
        file_id, blob_url = blob_storage.save_uploaded_file(
            file_bytes, 
            file.filename, 
            current_user.id, 
            user_building.id
        )
        
        # Process file and create scene graph
        scene_graph = scene_service.create_scene_graph_from_file(
            file.filename, 
            file_bytes
        )
        
        # Create drawing record with file path
        drawing = Drawing(
            filename=file.filename,
            title=scene_graph.title,
            building_id=user_building.id,
            scene_graph_id=scene_graph.diagram_id,
            uploaded_by=current_user.id,
            file_path=blob_url
        )
        db.add(drawing)
        db.commit()
        db.refresh(drawing)
        logger.info(f"Created drawing record: {drawing.id} for building {user_building.id} with blob: {blob_url}")
        
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
async def get_diagram_image(
    diagram_id: str,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        # Get current user from token (if provided)
        current_user = None
        if token:
            current_user = auth_service.get_current_user_from_token(db, token)
        
        # Find the drawing record with this scene_graph_id
        from auth_models import Drawing, Building
        
        if current_user:
            # Authenticated request - check ownership
            drawing = db.query(Drawing)\
                        .join(Building)\
                        .filter(
                            Drawing.scene_graph_id == diagram_id,
                            Building.owner_user_id == current_user.id
                        )\
                        .first()
        else:
            # Unauthenticated request - allow any drawing for now (public access)
            drawing = db.query(Drawing)\
                        .filter(Drawing.scene_graph_id == diagram_id)\
                        .first()
        
        if not drawing or not drawing.file_path:
            # Fallback to SimpleRiser.png for existing diagrams without file_path
            fallback_path = "SimpleRiser.png"
            if os.path.exists(fallback_path):
                return FileResponse(fallback_path, media_type="image/png")
            else:
                raise HTTPException(status_code=404, detail="Diagram image not found")
        
        # Stream blob content directly through backend
        try:
            if blob_storage.blob_service_client:
                # Stream from Azure Blob Storage
                blob_client = blob_storage.blob_service_client.get_blob_client(
                    container=blob_storage.container_name,
                    blob=drawing.file_path.replace(f"https://{blob_storage.account_name}.blob.core.windows.net/{blob_storage.container_name}/", "")
                )
                
                # Download blob content
                blob_data = blob_client.download_blob().readall()
                
                # Determine content type from file extension
                file_ext = os.path.splitext(drawing.filename)[1].lower()
                content_type_map = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg', 
                    '.jpeg': 'image/jpeg',
                    '.pdf': 'application/pdf'
                }
                content_type = content_type_map.get(file_ext, 'application/octet-stream')
                
                # Return blob content directly
                from fastapi.responses import Response
                return Response(content=blob_data, media_type=content_type)
            else:
                # Local storage fallback
                from file_storage import file_storage
                file_path = file_storage.get_file_path(drawing.file_path)
                if file_path and file_path.exists():
                    return FileResponse(str(file_path))
                else:
                    raise HTTPException(status_code=404, detail="Image file not found")
                    
        except Exception as e:
            logger.error(f"Error streaming blob content: {e}")
            raise HTTPException(status_code=404, detail="Image file not found")
        
    except HTTPException:
        raise
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