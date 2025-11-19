import logging
import uuid
from typing import Optional, List, Dict, Any
from models import SceneGraph, SceneGraphNode, SceneGraphRelationship, ComponentType, RelationshipType
from openai_client import OpenAIClient
from document_processor import DocumentProcessor
from database import db

logger = logging.getLogger(__name__)

class SceneGraphService:
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.doc_processor = DocumentProcessor()
    
    def create_scene_graph_from_file(self, filename: str, file_bytes: bytes) -> SceneGraph:
        try:
            # Process the file
            image_b64, text_content = self.doc_processor.process_file(filename, file_bytes)
            
            # Analyze with GPT-5
            scene_data = self.openai_client.analyze_diagram_with_gpt5(image_b64, text_content)
            
            # Convert to SceneGraph model
            scene_graph = self._convert_to_scene_graph(scene_data, filename)
            
            # Store in Neo4j
            success = db.store_scene_graph(scene_graph)
            if not success:
                raise Exception("Failed to store scene graph in database")
            
            logger.info(f"Scene graph created for {filename}: {len(scene_graph.nodes)} nodes, {len(scene_graph.relationships)} relationships")
            
            return scene_graph
            
        except Exception as e:
            logger.error(f"Failed to create scene graph: {e}")
            raise
    
    def _convert_to_scene_graph(self, scene_data: Dict[str, Any], filename: str) -> SceneGraph:
        diagram_id = str(uuid.uuid4())
        
        # Convert components to nodes
        nodes = []
        for comp_data in scene_data.get('components', []):
            try:
                node = SceneGraphNode(
                    id=comp_data.get('id', str(uuid.uuid4())),
                    type=ComponentType(comp_data.get('type', 'pipe')),
                    name=comp_data.get('name', 'Unknown'),
                    properties=comp_data.get('properties', {}),
                    position=comp_data.get('position'),
                    dimensions=comp_data.get('dimensions')
                )
                nodes.append(node)
            except Exception as e:
                logger.warning(f"Skipping invalid component: {e}")
                continue
        
        # Convert relationships
        relationships = []
        for rel_data in scene_data.get('relationships', []):
            try:
                relationship = SceneGraphRelationship(
                    source_id=rel_data.get('source_id'),
                    target_id=rel_data.get('target_id'),
                    type=RelationshipType(rel_data.get('type', 'CONNECTS_TO')),
                    properties=rel_data.get('properties')
                )
                relationships.append(relationship)
            except Exception as e:
                logger.warning(f"Skipping invalid relationship: {e}")
                continue
        
        # Create metadata
        metadata = scene_data.get('metadata', {})
        metadata['source_filename'] = filename
        metadata['processing_timestamp'] = str(uuid.uuid4())  # Use as timestamp placeholder
        
        scene_graph = SceneGraph(
            diagram_id=diagram_id,
            title=scene_data.get('title', f"Diagram from {filename}"),
            nodes=nodes,
            relationships=relationships,
            metadata=metadata
        )
        
        return scene_graph
    
    def query_scene_graphs(self, question: str, diagram_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            # Get the complete scene graph data
            if diagram_id:
                graph_data = self._get_complete_scene_graph(diagram_id)
            else:
                # If no specific diagram, get the most recent one
                diagrams = db.get_all_diagrams()
                if not diagrams:
                    raise ValueError("No diagrams found in database")
                diagram_id = diagrams[0]['diagram_id']
                graph_data = self._get_complete_scene_graph(diagram_id)
            
            if not graph_data:
                raise ValueError(f"No data found for diagram {diagram_id}")
            
            # Use GPT to analyze the graph and answer the question
            response = self.openai_client.answer_question_with_graph_context(question, graph_data)
            
            logger.info(f"Question answered using full graph context")
            return response
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            raise
    
    def _get_complete_scene_graph(self, diagram_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the complete scene graph data for a diagram"""
        try:
            # Get diagram info
            diagram_info = db.get_diagram_info(diagram_id)
            if not diagram_info:
                return None
            
            # Get all components
            components = db.execute_cypher("""
                MATCH (d:Diagram {id: $diagram_id})-[:CONTAINS]->(c:Component)
                RETURN c.id as id, c.type as type, c.name as name,
                       c.material as material, c.diameter as diameter, 
                       c.length as length, c.flow_direction as flow_direction,
                       c.position_x as position_x, c.position_y as position_y,
                       c.width as width, c.height as height
            """, {'diagram_id': diagram_id})
            
            # Get all relationships
            relationships = db.execute_cypher("""
                MATCH (d:Diagram {id: $diagram_id})-[:CONTAINS]->(c1:Component)
                MATCH (d)-[:CONTAINS]->(c2:Component)
                MATCH (c1)-[r]->(c2)
                WHERE type(r) IN ['CONNECTS_TO', 'FLOWS_TO', 'ABOVE', 'BELOW', 'PARALLEL_TO', 'SUPPORTS', 'CONTAINS']
                RETURN c1.id as source_id, c2.id as target_id, type(r) as relationship_type,
                       r.distance as distance, r.angle as angle
            """, {'diagram_id': diagram_id})
            
            # Structure the data
            graph_data = {
                'diagram': {
                    'id': diagram_id,
                    'title': diagram_info.get('title', 'Unknown'),
                    'diagram_type': diagram_info.get('diagram_type', ''),
                    'source_filename': diagram_info.get('source_filename', ''),
                    'building_zone': diagram_info.get('building_zone', ''),
                    'floor_level': diagram_info.get('floor_level', ''),
                    'scale': diagram_info.get('scale', '')
                },
                'components': components,
                'relationships': relationships,
                'summary': {
                    'total_components': len(components),
                    'total_relationships': len(relationships)
                }
            }
            
            return graph_data
            
        except Exception as e:
            logger.error(f"Failed to get complete scene graph: {e}")
            return None
    
    
    def get_diagram_summary(self, diagram_id: str) -> Optional[Dict[str, Any]]:
        try:
            info = db.get_diagram_info(diagram_id)
            if not info:
                return None
            
            # Get sample components
            sample_components = db.execute_cypher("""
                MATCH (d:Diagram {id: $diagram_id})-[:CONTAINS]->(c:Component)
                RETURN c.name as name, c.type as type, c.properties as properties
                LIMIT 5
            """, {'diagram_id': diagram_id})
            
            info['sample_components'] = sample_components
            return info
            
        except Exception as e:
            logger.error(f"Failed to get diagram summary: {e}")
            return None
    
    def list_all_diagrams(self) -> List[Dict[str, Any]]:
        try:
            return db.get_all_diagrams()
        except Exception as e:
            logger.error(f"Failed to list diagrams: {e}")
            return []