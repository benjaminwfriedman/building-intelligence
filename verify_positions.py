#!/usr/bin/env python3

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import db
from config import Config

def verify_component_positions():
    """Fetch positions from Neo4j and plot them on SimpleRiser.png for verification"""
    
    try:
        # Check if image exists
        image_path = "SimpleRiser.png"
        if not os.path.exists(image_path):
            print(f"❌ {image_path} not found")
            return
        
        print("✓ Loading SimpleRiser.png...")
        
        # Load the image
        img = Image.open(image_path)
        img_array = plt.imread(image_path)
        
        print(f"✓ Image loaded: {img.size[0]}x{img.size[1]} pixels")
        
        # Get all diagrams
        diagrams = db.get_all_diagrams()
        if not diagrams:
            print("❌ No diagrams found in database")
            return
        
        # Use the first (most recent) diagram
        diagram_id = diagrams[0]['diagram_id']
        diagram_title = diagrams[0].get('title', 'Unknown')
        
        print(f"✓ Using diagram: {diagram_title}")
        print(f"  Diagram ID: {diagram_id}")
        
        # Fetch component positions from Neo4j
        components = db.execute_cypher("""
            MATCH (d:Diagram {id: $diagram_id})-[:CONTAINS]->(c:Component)
            RETURN c.id as id, c.name as name, c.type as type,
                   c.position_x as position_x, c.position_y as position_y,
                   c.material as material, c.diameter as diameter
            ORDER BY c.id
        """, {'diagram_id': diagram_id})
        
        if not components:
            print("❌ No components found for diagram")
            return
        
        print(f"✓ Found {len(components)} components in database")
        
        # Create the plot
        fig, ax = plt.subplots(1, 1, figsize=(12, 10))
        ax.imshow(img_array)
        ax.set_title(f"Component Position Verification\n{diagram_title}", fontsize=14, pad=20)
        
        # Plot each component position - testing percentage interpretation
        for i, component in enumerate(components):
            comp_id = component['id']
            name = component['name']
            x_pos_raw = component.get('position_x', 0) or 0
            y_pos_raw = component.get('position_y', 0) or 0
            material = component.get('material', '')
            diameter = component.get('diameter', '')
            
            # Test if positions are percentages (0-100) of image dimensions
            x_pos_pixels = (x_pos_raw / 100.0) * img.size[0] if x_pos_raw <= 100 else x_pos_raw
            y_pos_pixels = (y_pos_raw / 100.0) * img.size[1] if y_pos_raw <= 100 else y_pos_raw
            
            print(f"  {i+1:2d}. {comp_id}: {name}")
            print(f"      Raw Position: ({x_pos_raw}, {y_pos_raw})")
            print(f"      As Percentages: ({x_pos_pixels:.1f}, {y_pos_pixels:.1f}) pixels")
            print(f"      Material: {material}, Diameter: {diameter}")
            
            # Plot the badge at percentage-based coordinates
            circle = patches.Circle((x_pos_pixels, y_pos_pixels), radius=15, 
                                  facecolor='blue', edgecolor='white', 
                                  linewidth=2, alpha=0.8)
            ax.add_patch(circle)
            
            # Add number label
            ax.text(x_pos_pixels, y_pos_pixels, str(i + 1), 
                   ha='center', va='center', 
                   color='white', fontweight='bold', fontsize=10)
            
            # Add component ID as small text nearby
            ax.text(x_pos_pixels + 20, y_pos_pixels - 20, comp_id, 
                   ha='left', va='center', 
                   color='red', fontweight='bold', fontsize=8,
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
        
        # Set axis properties
        ax.set_xlim(0, img.size[0])
        ax.set_ylim(img.size[1], 0)  # Invert Y axis for image coordinates
        ax.set_xlabel('X Coordinate (pixels)')
        ax.set_ylabel('Y Coordinate (pixels)')
        ax.grid(True, alpha=0.3)
        
        # Add legend
        ax.text(0.02, 0.98, f"Database Positions for {len(components)} Components\nBlue circles = Database coordinates\nRed labels = Component IDs", 
                transform=ax.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        print(f"\n📊 Displaying verification plot...")
        print(f"   Blue circles show database positions")
        print(f"   Red labels show component IDs")
        print(f"   Compare with actual component locations on diagram")
        
        plt.tight_layout()
        plt.show()
        
        print(f"\n✅ Verification complete!")
        print(f"   Check if blue badges align with actual plumbing components")
        print(f"   Note any components that need position corrections")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Neo4j database connection configured")
        print("2. At least one processed diagram in the database")
        print("3. matplotlib and Pillow installed")

if __name__ == "__main__":
    verify_component_positions()