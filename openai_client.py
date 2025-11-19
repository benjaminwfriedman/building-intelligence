import json
import logging
from typing import Optional, Dict, Any
from openai import OpenAI
from config import Config

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.gpt5_model = Config.GPT5_MODEL
        self.gpt4o_mini_model = Config.GPT4O_MINI_MODEL
    
    def analyze_diagram_with_gpt5(self, image_base64: str, text_content: Optional[str] = None) -> Dict[str, Any]:
        system_prompt = """You are an expert in analyzing engineering diagrams and creating scene graphs. 
        Your task is to extract a comprehensive scene graph from the provided engineering diagram.
        
        Analyze the diagram and identify:
        1. Components (pipes, fixtures, valves, fittings, etc.)
        2. Spatial relationships (connections, above/below, parallel, etc.)
        3. Properties (materials, dimensions, flow directions)
        4. Hierarchical structure (floors, zones, systems)
        
        Return a JSON object with this structure:
        {
            "title": "Brief description of the diagram",
            "components": [
                {
                    "id": "unique_identifier",
                    "type": "pipe|fixture|connector|vent|valve|fitting",
                    "name": "descriptive_name",
                    "properties": {
                        "material": "cast_iron|abs|pvc|copper|galvanized|lead|brass",
                        "diameter": "size_in_inches",
                        "length": "length_if_visible",
                        "flow_direction": "direction_if_applicable"
                    },
                    "position": {"x": 0, "y": 0},
                    "dimensions": {"width": 0, "height": 0}
                }
            ],
            "relationships": [
                {
                    "source_id": "component_id",
                    "target_id": "component_id", 
                    "type": "CONNECTS_TO|ABOVE|BELOW|CONTAINS|FLOWS_TO|SUPPORTS|PARALLEL_TO",
                    "properties": {"distance": "if_measurable", "angle": "if_applicable"}
                }
            ],
            "metadata": {
                "diagram_type": "plumbing|electrical|mechanical|structural",
                "scale": "if_visible",
                "floor_level": "if_applicable",
                "building_zone": "if_applicable"
            }
        }
        
        Be thorough and precise. Include all visible components and their relationships."""
        
        user_prompt = "Analyze this engineering diagram and create a comprehensive scene graph as specified."
        if text_content:
            user_prompt += f"\n\nAdditional text content extracted from document:\n{text_content[:1000]}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.gpt5_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_completion_tokens=4000
            )
            
            content = response.choices[0].message.content
            logger.info(f"Raw GPT-5 response: {content[:500]}...")
            
            # Parse JSON response
            try:
                # Try to extract JSON from response if wrapped in markdown
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    json_content = content[json_start:json_end].strip()
                    scene_data = json.loads(json_content)
                elif "```" in content:
                    # Handle case where it's wrapped in code blocks without json tag
                    json_start = content.find("```") + 3
                    json_end = content.rfind("```")
                    json_content = content[json_start:json_end].strip()
                    scene_data = json.loads(json_content)
                else:
                    # Try direct parsing
                    scene_data = json.loads(content)
                
                logger.info(f"GPT-5 analysis completed: {len(scene_data.get('components', []))} components")
                return scene_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse GPT-5 JSON response: {e}")
                logger.error(f"Content: {content}")
                raise ValueError(f"Could not parse JSON from GPT-5 response: {e}")
                
        except Exception as e:
            logger.error(f"GPT-5 analysis failed: {e}")
            raise
    
    def answer_question_with_graph_context(self, question: str, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """Answer questions about engineering diagrams using complete graph context"""
        
        system_prompt = """You are an expert engineer analyzing scene graphs from engineering diagrams.
        
        You will receive complete scene graph data including components and relationships.
        Analyze this data and answer questions about the engineering system.
        
        Provide detailed, technical answers that demonstrate understanding of:
        - System topology and connections
        - Material properties and specifications  
        - Spatial relationships and flow patterns
        - Potential failure modes and impacts
        
        Always explain your reasoning and cite specific components when relevant."""
        
        user_prompt = f"Question: {question}\n\nComplete Scene Graph Data:\n{json.dumps(graph_data, indent=2)}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.gpt4o_mini_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_completion_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # Return simple response format
            return {
                "answer": content,
                "confidence": 0.9
            }
                
        except Exception as e:
            logger.error(f"Question answering failed: {e}")
            raise