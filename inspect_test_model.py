#!/usr/bin/env python3
"""Inspect the test_model.vox to see what's actually in it"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from vox_utils import read_vox_file, VoxelModel

def inspect_model(filename: str):
    """Inspect a model and print detailed information"""
    filepath = Path("vox") / f"{filename}.vox"
    
    if not filepath.exists():
        print(f"Error: {filepath} not found")
        return
    
    print("=" * 60)
    print(f"Inspecting: {filename}.vox")
    print("=" * 60)
    
    model = read_vox_file(filepath)
    
    print(f"\nDimensions: {model.size_x}x{model.size_y}x{model.size_z}")
    print(f"Total voxels: {model.get_voxel_count()}")
    
    # Get bounds
    bounds = model.get_bounds()
    print(f"Actual bounds: {bounds[0]}x{bounds[1]}x{bounds[2]}")
    
    # Count by color
    color_counts = model.count_colors()
    print(f"\nColors used: {len(color_counts)}")
    for color_idx, count in sorted(color_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  Color {color_idx}: {count} voxels")
    
    # Find connected components
    components = model.find_connected_components()
    print(f"\nConnected components: {len(components)}")
    for i, comp in enumerate(components, 1):
        b = comp['bounds']
        print(f"  Component {i}: {comp['voxel_count']} voxels")
        print(f"    Bounds: ({b['min_x']},{b['min_y']},{b['min_z']}) to ({b['max_x']},{b['max_y']},{b['max_z']})")
    
    # Check specific regions
    print("\n" + "=" * 60)
    print("Checking Specific Regions:")
    print("=" * 60)
    
    # Check the partially cleared box area
    print("\n1. Partially cleared box area (5,5,5 to 10,10,10):")
    box_voxels = 0
    for x in range(5, 11):
        for y in range(5, 11):
            for z in range(5, 11):
                if model.get_voxel(x, y, z) > 0:
                    box_voxels += 1
    print(f"   Voxels present: {box_voxels} (expected: partial, original was 216)")
    
    # Check hole at (7,7,7)
    hole_color = model.get_voxel(7, 7, 7)
    print(f"   Hole at (7,7,7): {'Empty' if hole_color == 0 else f'Color {hole_color}'}")
    
    # Check torus center
    print("\n2. Torus center area (15,15,15):")
    torus_color = model.get_voxel(15, 15, 15)
    print(f"   Center voxel: {'Empty' if torus_color == 0 else f'Color {torus_color}'}")
    # Check around torus
    torus_voxels = 0
    for x in range(10, 21):
        for y in range(10, 21):
            for z in range(10, 21):
                if model.get_voxel(x, y, z) == 2:  # Green
                    torus_voxels += 1
    print(f"   Green voxels in torus area: {torus_voxels}")
    
    # Check cone base
    print("\n3. Cone base area (15,0,15):")
    cone_base_color = model.get_voxel(15, 0, 15)
    print(f"   Base center: {'Empty' if cone_base_color == 0 else f'Color {cone_base_color}'}")
    cone_voxels = 0
    for y in range(0, 11):
        if model.get_voxel(15, y, 15) == 3:  # Blue
            cone_voxels += 1
    print(f"   Blue voxels in cone area: {cone_voxels}")
    
    # Check mirrored cubes
    print("\n4. Mirrored cubes:")
    cube1_voxels = 0
    for x in range(0, 4):
        for y in range(0, 4):
            for z in range(0, 4):
                if model.get_voxel(x, y, z) == 5:  # Magenta
                    cube1_voxels += 1
    print(f"   Original cube (0,0,0 to 3,3,3): {cube1_voxels} magenta voxels")
    
    cube2_voxels = 0
    for x in range(27, 31):
        for y in range(0, 4):
            for z in range(0, 4):
                if model.get_voxel(x, y, z) == 5:  # Magenta
                    cube2_voxels += 1
    print(f"   Mirrored cube (27,0,0 to 30,3,3): {cube2_voxels} magenta voxels")
    
    # Check rotated box
    print("\n5. Rotated box area (20,5,5 to 22,7,7):")
    rotated_voxels = 0
    for x in range(20, 23):
        for y in range(5, 8):
            for z in range(5, 8):
                if model.get_voxel(x, y, z) == 4:  # Yellow
                    rotated_voxels += 1
    print(f"   Yellow voxels: {rotated_voxels}")
    
    # Check moved box
    print("\n6. Moved box:")
    original_pos_voxels = 0
    for x in range(25, 28):
        for y in range(0, 3):
            for z in range(0, 3):
                if model.get_voxel(x, y, z) == 6:  # Cyan
                    original_pos_voxels += 1
    print(f"   Original position (25,0,0 to 27,2,2): {original_pos_voxels} cyan voxels")
    
    moved_pos_voxels = 0
    for x in range(25, 28):
        for y in range(5, 8):
            for z in range(0, 3):
                if model.get_voxel(x, y, z) == 6:  # Cyan
                    moved_pos_voxels += 1
    print(f"   Moved position (25,5,0 to 27,7,2): {moved_pos_voxels} cyan voxels")
    
    # Check extruded column
    print("\n7. Extruded column (0,10,0 to 2,10,2, extruded +5):")
    column_voxels = 0
    for x in range(0, 3):
        for y in range(10, 16):
            for z in range(0, 3):
                if model.get_voxel(x, y, z) == 8:
                    column_voxels += 1
    print(f"   Color 8 voxels in column area: {column_voxels}")
    
    print("\n" + "=" * 60)
    print("Inspection Complete")
    print("=" * 60)

if __name__ == "__main__":
    inspect_model("test_model")
