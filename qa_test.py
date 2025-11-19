#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scene_graph_service import SceneGraphService
from config import Config

def test_qa_with_existing_graph():
    """Test natural language queries against existing scene graph"""
    
    try:
        # Initialize service
        service = SceneGraphService()
        print("✓ Scene graph service initialized")
        
        # Get list of existing diagrams
        diagrams = service.list_all_diagrams()
        
        if not diagrams:
            print("❌ No diagrams found in database. Please run the main processing first.")
            return
        
        print(f"✓ Found {len(diagrams)} diagram(s) in database")
        
        # Use the most recent diagram
        latest_diagram = diagrams[0]  # Assuming sorted by creation time DESC
        diagram_id = latest_diagram['diagram_id']
        
        print(f"✓ Using diagram: {latest_diagram.get('title', 'Untitled')}")
        print(f"  - Diagram ID: {diagram_id}")
        print(f"  - Components: {latest_diagram.get('component_count', 'Unknown')}")
        
        # Test questions about the SimpleRiser plumbing system
        test_questions = [
            # Basic component queries
            "How many components are in this plumbing system?",
            "What types of fixtures are connected to the system?",
            "What materials are used for the pipes?",
            
            # Spatial relationships
            "Which fixtures are on the top floor?",
            "What components connect to the left vertical stack?",
            "Show me all the water closets in the system",
            
            # Technical queries
            "What are the pipe diameters used in this system?",
            "Which pipes have a 3-inch diameter?",
            "What is the flow direction from fixtures to the main stack?",
            
            # System analysis
            "If the left vertical vent stack gets clogged, what fixtures would be impacted?",
            "Which components are connected in parallel?",
            "What is the relationship between the kitchen sink and the main stack?",
            
            # Advanced queries
            "How many floors does this plumbing system serve?",
            "What type of diagram is this?",
            "Which fixtures drain into the building drain on the right side?",
        ]
        
        print(f"\n🧪 Testing {len(test_questions)} natural language queries...\n")
        
        successful_queries = 0
        
        for i, question in enumerate(test_questions, 1):
            print(f"[{i:2d}/{len(test_questions)}] Q: {question}")
            
            try:
                result = service.query_scene_graphs(question, diagram_id)
                
                print(f"       A: {result['answer']}")
                print(f"       Confidence: {result['confidence']:.2f}")
                
                successful_queries += 1
                print("       ✅ Success\n")
                
            except Exception as e:
                print(f"       ❌ Error: {e}\n")
        
        # Summary
        success_rate = (successful_queries / len(test_questions)) * 100
        print(f"📊 Test Summary:")
        print(f"   Successful queries: {successful_queries}/{len(test_questions)}")
        print(f"   Success rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("   🎉 Excellent performance!")
        elif success_rate >= 60:
            print("   👍 Good performance")
        else:
            print("   ⚠️  Needs improvement")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("\nMake sure you have:")
        print("1. Set up your .env file with valid credentials")
        print("2. OpenAI API key configured")
        print("3. Neo4j Aura database accessible")
        print("4. At least one diagram processed in the database")

if __name__ == "__main__":
    test_qa_with_existing_graph()