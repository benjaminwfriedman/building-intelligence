import logging
import time
from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
from config import Config
from models import SceneGraph

logger = logging.getLogger(__name__)

class Neo4jDatabase:
    def __init__(self):
        self.driver = None
        self.connect()
    
    def connect(self):
        try:
            Config.validate()
            self.driver = GraphDatabase.driver(
                Config.NEO4J_URI,
                auth=(Config.NEO4J_USERNAME, Config.NEO4J_PASSWORD),
                max_connection_lifetime=60*10  # 10 minutes
            )
            logger.info("Connected to Neo4j Aura")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        if self.driver:
            self.driver.close()
    
    def create_schema(self):
        with self.driver.session() as session:
            # Create constraints and indexes
            constraints = [
                "CREATE CONSTRAINT component_id IF NOT EXISTS FOR (c:Component) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT diagram_id IF NOT EXISTS FOR (d:Diagram) REQUIRE d.id IS UNIQUE",
            ]
            
            indexes = [
                "CREATE INDEX component_type IF NOT EXISTS FOR (c:Component) ON (c.type)",
                "CREATE INDEX diagram_title IF NOT EXISTS FOR (d:Diagram) ON (d.title)",
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    logger.warning(f"Constraint creation warning: {e}")
            
            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    logger.warning(f"Index creation warning: {e}")
    
    def store_scene_graph(self, scene_graph: SceneGraph) -> bool:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self.driver.session() as session:
                    # Create diagram node - flatten metadata to avoid nested objects
                    flattened_metadata = {}
                    for key, value in scene_graph.metadata.items():
                        if isinstance(value, (dict, list)):
                            flattened_metadata[key] = str(value)
                        else:
                            flattened_metadata[key] = value
                    
                    session.run("""
                        MERGE (d:Diagram {id: $diagram_id})
                        SET d.title = $title,
                            d.diagram_type = $diagram_type,
                            d.source_filename = $source_filename,
                            d.processing_timestamp = $processing_timestamp,
                            d.scale = $scale,
                            d.building_zone = $building_zone,
                            d.floor_level = $floor_level,
                            d.created_at = datetime()
                    """, 
                    diagram_id=scene_graph.diagram_id,
                    title=scene_graph.title,
                    diagram_type=flattened_metadata.get('diagram_type', ''),
                    source_filename=flattened_metadata.get('source_filename', ''),
                    processing_timestamp=flattened_metadata.get('processing_timestamp', ''),
                    scale=flattened_metadata.get('scale', ''),
                    building_zone=flattened_metadata.get('building_zone', ''),
                    floor_level=flattened_metadata.get('floor_level', '')
                    )
                    
                    # Create component nodes
                    for node in scene_graph.nodes:
                        # Flatten properties
                        flattened_props = {}
                        if node.properties:
                            for key, value in node.properties.items():
                                if isinstance(value, (dict, list)):
                                    flattened_props[key] = str(value)
                                else:
                                    flattened_props[key] = value
                        
                        # Flatten position and dimensions
                        pos_x = node.position.get('x', 0) if node.position else 0
                        pos_y = node.position.get('y', 0) if node.position else 0
                        dim_width = node.dimensions.get('width', 0) if node.dimensions else 0
                        dim_height = node.dimensions.get('height', 0) if node.dimensions else 0
                        
                        session.run("""
                            MERGE (c:Component {id: $id})
                            SET c.type = $type,
                                c.name = $name,
                                c.material = $material,
                                c.diameter = $diameter,
                                c.length = $length,
                                c.flow_direction = $flow_direction,
                                c.position_x = $pos_x,
                                c.position_y = $pos_y,
                                c.width = $width,
                                c.height = $height
                            WITH c
                            MATCH (d:Diagram {id: $diagram_id})
                            MERGE (d)-[:CONTAINS]->(c)
                        """,
                        id=node.id,
                        type=node.type.value,
                        name=node.name,
                        material=flattened_props.get('material', ''),
                        diameter=flattened_props.get('diameter', ''),
                        length=flattened_props.get('length', ''),
                        flow_direction=flattened_props.get('flow_direction', ''),
                        pos_x=pos_x,
                        pos_y=pos_y,
                        width=dim_width,
                        height=dim_height,
                        diagram_id=scene_graph.diagram_id
                        )
                    
                    # Create relationships
                    for rel in scene_graph.relationships:
                        # Flatten relationship properties
                        rel_props = {}
                        if rel.properties:
                            for key, value in rel.properties.items():
                                if isinstance(value, (dict, list)):
                                    rel_props[key] = str(value)
                                else:
                                    rel_props[key] = value
                        
                        session.run(f"""
                            MATCH (source:Component {{id: $source_id}})
                            MATCH (target:Component {{id: $target_id}})
                            MERGE (source)-[r:{rel.type.value}]->(target)
                            SET r.distance = $distance,
                                r.angle = $angle
                        """,
                        source_id=rel.source_id,
                        target_id=rel.target_id,
                        distance=rel_props.get('distance', ''),
                        angle=rel_props.get('angle', '')
                        )
                    
                    logger.info(f"Scene graph {scene_graph.diagram_id} stored successfully")
                    return True
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    logger.error(f"Failed to store scene graph after {max_retries} attempts: {e}")
                    return False
    
    def execute_cypher(self, query: str, parameters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Failed to execute Cypher query: {e}")
            raise
    
    def get_diagram_info(self, diagram_id: str) -> Optional[Dict[str, Any]]:
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (d:Diagram {id: $diagram_id})
                    OPTIONAL MATCH (d)-[:CONTAINS]->(c:Component)
                    RETURN d.title as title, 
                           d.metadata as metadata,
                           count(c) as component_count
                """, diagram_id=diagram_id)
                
                record = result.single()
                return record.data() if record else None
        except Exception as e:
            logger.error(f"Failed to get diagram info: {e}")
            return None
    
    def get_all_diagrams(self) -> List[Dict[str, Any]]:
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (d:Diagram)
                    OPTIONAL MATCH (d)-[:CONTAINS]->(c:Component)
                    RETURN d.id as diagram_id,
                           d.title as title,
                           d.created_at as created_at,
                           count(c) as component_count
                    ORDER BY d.created_at DESC
                """)
                
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Failed to get diagrams: {e}")
            return []
    
    def health_check(self) -> bool:
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1")
                return result.single() is not None
        except Exception:
            return False

# Global database instance
db = Neo4jDatabase()