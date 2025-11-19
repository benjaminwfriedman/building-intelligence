from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from enum import Enum

class ComponentType(str, Enum):
    PIPE = "pipe"
    FIXTURE = "fixture"
    CONNECTOR = "connector"
    VENT = "vent"
    VALVE = "valve"
    FITTING = "fitting"

class RelationshipType(str, Enum):
    CONNECTS_TO = "CONNECTS_TO"
    ABOVE = "ABOVE"
    BELOW = "BELOW"
    CONTAINS = "CONTAINS"
    FLOWS_TO = "FLOWS_TO"
    SUPPORTS = "SUPPORTS"
    PARALLEL_TO = "PARALLEL_TO"

class SceneGraphNode(BaseModel):
    id: str
    type: ComponentType
    name: str
    properties: Dict[str, Any]
    position: Optional[Dict[str, float]] = None  # x, y coordinates
    dimensions: Optional[Dict[str, float]] = None  # width, height, length

class SceneGraphRelationship(BaseModel):
    source_id: str
    target_id: str
    type: RelationshipType
    properties: Optional[Dict[str, Any]] = None

class SceneGraph(BaseModel):
    diagram_id: str
    title: Optional[str] = None
    nodes: List[SceneGraphNode]
    relationships: List[SceneGraphRelationship]
    metadata: Dict[str, Any] = {}

class DiagramUpload(BaseModel):
    filename: str
    content_type: str

class QueryRequest(BaseModel):
    question: str
    graph_id: Optional[str] = None  # Query specific graph or all graphs

class QueryResponse(BaseModel):
    answer: str
    confidence: float