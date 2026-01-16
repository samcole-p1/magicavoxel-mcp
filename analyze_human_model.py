#!/usr/bin/env python3
"""Analyze the human character model and identify improvements"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from vox_utils import read_vox_file

def analyze_human():
    """Analyze the human character model"""
    filepath = Path("vox") / "human_character.vox"
    
    if not filepath.exists():
        print(f"Error: {filepath} not found")
        return
    
    print("=" * 60)
    print("HUMAN CHARACTER MODEL ANALYSIS")
    print("=" * 60)
    
    model = read_vox_file(filepath)
    
    print(f"\nDimensions: {model.size_x}×{model.size_y}×{model.size_z} voxels")
    print(f"Total voxels: {model.get_voxel_count()}")
    
    bounds = model.get_bounds()
    print(f"Actual bounds: {bounds[0]}×{bounds[1]}×{bounds[2]}")
    
    # Count by color
    color_counts = model.count_colors()
    print(f"\nColors used: {len(color_counts)}")
    for color_idx, count in sorted(color_counts.items(), key=lambda x: x[1], reverse=True):
        r, g, b, a = model.palette[color_idx]
        print(f"  Color {color_idx}: {count} voxels (RGB: {r},{g},{b})")
    
    # Analyze proportions
    print("\n" + "=" * 60)
    print("PROPORTION ANALYSIS:")
    print("=" * 60)
    
    # Head
    head_voxels = sum(1 for (x,y,z), c in model.voxels.items() 
                     if y >= 24 and c > 0)
    print(f"Head area (y>=24): {head_voxels} voxels")
    
    # Torso
    torso_voxels = sum(1 for (x,y,z), c in model.voxels.items() 
                      if 12 <= y < 24 and c > 0)
    print(f"Torso area (y=12-23): {torso_voxels} voxels")
    
    # Legs
    leg_voxels = sum(1 for (x,y,z), c in model.voxels.items() 
                    if y < 12 and c > 0)
    print(f"Legs area (y<12): {leg_voxels} voxels")
    
    # Arms
    arm_voxels = sum(1 for (x,y,z), c in model.voxels.items() 
                    if (x < 5 or x > 11) and 12 <= y < 24 and c > 0)
    print(f"Arms area: {arm_voxels} voxels")
    
    # Check symmetry
    print("\n" + "=" * 60)
    print("SYMMETRY CHECK:")
    print("=" * 60)
    
    center_x = model.size_x // 2
    symmetric = True
    issues = []
    
    for (x, y, z), color in model.voxels.items():
        mirror_x = 2 * center_x - x
        if mirror_x >= 0 and mirror_x < model.size_x:
            if (mirror_x, y, z) not in model.voxels:
                symmetric = False
                issues.append(f"Missing mirror at ({mirror_x},{y},{z}) for ({x},{y},{z})")
                if len(issues) >= 5:
                    break
    
    if symmetric:
        print("[OK] Model appears symmetric")
    else:
        print(f"[ISSUE] Model has {len(issues)} symmetry issues")
        print("First few issues:")
        for issue in issues[:3]:
            print(f"  {issue}")
    
    # Check connectivity
    components = model.find_connected_components()
    print(f"\nConnected components: {len(components)}")
    if len(components) == 1:
        print("[OK] Character is one solid piece")
    else:
        print("[ISSUE] Character has disconnected pieces:")
        for i, comp in enumerate(components, 1):
            b = comp['bounds']
            print(f"  Component {i}: {comp['voxel_count']} voxels at ({b['min_x']},{b['min_y']},{b['min_z']})")
    
    # Check for gaps/holes
    print("\n" + "=" * 60)
    print("STRUCTURE ANALYSIS:")
    print("=" * 60)
    
    # Check if head connects to neck
    head_bottom = min(y for (x,y,z), c in model.voxels.items() if y >= 24 and c > 0)
    neck_top = max(y for (x,y,z), c in model.voxels.items() if y < 24 and 6 <= x <= 10 and 6 <= z <= 10 and c > 0)
    if head_bottom - neck_top > 1:
        print(f"[ISSUE] Gap between head (y={head_bottom}) and neck (y={neck_top})")
    else:
        print(f"[OK] Head connects to neck (head y={head_bottom}, neck y={neck_top})")
    
    # Check if arms connect to torso
    arm_connections = 0
    for y in range(12, 24):
        for z in range(5, 11):
            if (5, y, z) in model.voxels and (6, y, z) in model.voxels:
                arm_connections += 1
            if (11, y, z) in model.voxels and (10, y, z) in model.voxels:
                arm_connections += 1
    
    if arm_connections > 0:
        print(f"[OK] Arms connect to torso ({arm_connections} connection points)")
    else:
        print("[ISSUE] Arms may not connect properly to torso")
    
    # Check if legs connect to torso
    leg_connections = 0
    for x in range(6, 11):
        for z in range(6, 11):
            if (x, 11, z) in model.voxels and (x, 12, z) in model.voxels:
                leg_connections += 1
    
    if leg_connections > 0:
        print(f"[OK] Legs connect to torso ({leg_connections} connection points)")
    else:
        print("[ISSUE] Legs may not connect properly to torso")
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    analyze_human()
