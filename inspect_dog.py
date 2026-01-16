#!/usr/bin/env python3
"""Inspect the Minecraft dog model"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from vox_utils import read_vox_file

def inspect_dog():
    """Inspect the dog model"""
    filepath = Path("vox") / "minecraft_dog.vox"
    
    if not filepath.exists():
        print(f"Error: {filepath} not found")
        return
    
    print("=" * 60)
    print("MINECRAFT DOG MODEL INSPECTION")
    print("=" * 60)
    
    model = read_vox_file(filepath)
    
    print(f"\nDimensions: {model.size_x}×{model.size_y}×{model.size_z} voxels")
    print(f"Total voxels: {model.get_voxel_count()}")
    
    bounds = model.get_bounds()
    print(f"Actual bounds: {bounds[0]}×{bounds[1]}×{bounds[2]}")
    print(f"Minecraft scale: ~{bounds[0]/16:.2f} × {bounds[1]/16:.2f} × {bounds[2]/16:.2f} blocks")
    
    # Count by color
    color_counts = model.count_colors()
    print(f"\nColors used: {len(color_counts)}")
    for color_idx, count in sorted(color_counts.items(), key=lambda x: x[1], reverse=True):
        r, g, b, a = model.palette[color_idx]
        print(f"  Color {color_idx}: {count} voxels (RGB: {r},{g},{b})")
    
    # Check components
    components = model.find_connected_components()
    print(f"\nConnected components: {len(components)}")
    if len(components) == 1:
        print("  [OK] Dog is one solid piece (correct)")
    else:
        print("  [WARNING] Dog has multiple disconnected pieces")
        for i, comp in enumerate(components, 1):
            b = comp['bounds']
            print(f"    Component {i}: {comp['voxel_count']} voxels")
    
    # Check key features
    print("\n" + "=" * 60)
    print("FEATURE CHECK:")
    print("=" * 60)
    
    # Check head
    head_voxels = sum(1 for (x,y,z), c in model.voxels.items() 
                     if 17 <= z <= 23 and c > 0)
    print(f"Head area voxels: {head_voxels}")
    
    # Check body
    body_voxels = sum(1 for (x,y,z), c in model.voxels.items() 
                     if 6 <= z <= 16 and c > 0)
    print(f"Body area voxels: {body_voxels}")
    
    # Check legs
    leg_voxels = sum(1 for (x,y,z), c in model.voxels.items() 
                    if y <= 5 and c > 0)
    print(f"Leg area voxels: {leg_voxels}")
    
    # Check tail
    tail_voxels = sum(1 for (x,y,z), c in model.voxels.items() 
                     if z <= 5 and c > 0)
    print(f"Tail area voxels: {tail_voxels}")
    
    print("\n" + "=" * 60)
    print("INSPECTION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    inspect_dog()
