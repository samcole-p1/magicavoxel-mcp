#!/usr/bin/env python3
"""Analyze discrepancies between expected and actual test model"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from vox_utils import read_vox_file

def analyze():
    """Analyze what went wrong"""
    model = read_vox_file(Path("vox") / "test_model.vox")
    
    print("=" * 60)
    print("ANALYZING DISCREPANCIES")
    print("=" * 60)
    
    # Issue 1: Torus size
    print("\n1. TORUS SIZE ISSUE:")
    print("   Expected: Torus at (15,15,15) with major_r=8, minor_r=3")
    print("   Should create ~500-800 voxels, but got 1348 voxels")
    print("   Component bounds: (4,12,4) to (26,18,26)")
    print("   This suggests the torus might be connecting to the cone!")
    
    # Check if torus and cone are connected
    torus_voxels = sum(1 for (x,y,z), c in model.voxels.items() 
                      if c == 2 and 4 <= x <= 26 and 12 <= y <= 18 and 4 <= z <= 26)
    cone_voxels = sum(1 for (x,y,z), c in model.voxels.items() 
                     if c == 3 and 10 <= x <= 20 and 0 <= y <= 9 and 10 <= z <= 20)
    
    print(f"   Torus voxels (color 2): {torus_voxels}")
    print(f"   Cone voxels (color 3): {cone_voxels}")
    
    # Check if they touch
    print("\n   Checking if torus and cone connect...")
    torus_y_min = min(y for (x,y,z), c in model.voxels.items() if c == 2)
    cone_y_max = max(y for (x,y,z), c in model.voxels.items() if c == 3)
    print(f"   Torus lowest Y: {torus_y_min}")
    print(f"   Cone highest Y: {cone_y_max}")
    print(f"   Gap: {torus_y_min - cone_y_max} voxels")
    
    # Issue 2: Mirrored cube
    print("\n2. MIRRORED CUBE ISSUE:")
    print("   Expected: 64 voxels (4×4×4) in mirrored cube")
    print("   Actual: 55 voxels")
    print("   Missing: 9 voxels")
    
    # Check what's missing
    print("\n   Checking mirrored cube region (27,0,0 to 30,3,3):")
    missing = []
    for x in range(27, 31):
        for y in range(0, 4):
            for z in range(0, 4):
                if model.get_voxel(x, y, z) != 5:
                    missing.append((x, y, z))
    
    print(f"   Missing voxels: {len(missing)}")
    if missing:
        print(f"   First few missing: {missing[:5]}")
        # Check if they're out of bounds
        out_of_bounds = [m for m in missing if m[0] >= 30 or m[1] >= 30 or m[2] >= 30]
        if out_of_bounds:
            print(f"   Out of bounds voxels: {len(out_of_bounds)}")
            print("   ISSUE: Mirror operation is placing voxels outside model bounds!")
    
    # Issue 3: Component count
    print("\n3. COMPONENT COUNT ISSUE:")
    print("   Expected: 7 components")
    print("   Actual: 8 components")
    components = model.find_connected_components()
    print("\n   Component breakdown:")
    for i, comp in enumerate(components, 1):
        b = comp['bounds']
        print(f"   {i}. {comp['voxel_count']} voxels: ({b['min_x']},{b['min_y']},{b['min_z']}) to ({b['max_x']},{b['max_y']},{b['max_z']})")
    
    # Check if torus and cone are separate
    print("\n   Checking if torus (color 2) and cone (color 3) are separate...")
    # Find a torus voxel and a cone voxel, check if they're connected
    torus_pos = next(((x,y,z) for (x,y,z), c in model.voxels.items() if c == 2), None)
    cone_pos = next(((x,y,z) for (x,y,z), c in model.voxels.items() if c == 3), None)
    
    if torus_pos and cone_pos:
        # Simple check: are they in the same component?
        from collections import deque
        visited = set()
        queue = deque([torus_pos])
        visited.add(torus_pos)
        found_cone = False
        
        while queue:
            x, y, z = queue.popleft()
            if (x, y, z) == cone_pos:
                found_cone = True
                break
            for dx, dy, dz in [(1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)]:
                neighbor = (x+dx, y+dy, z+dz)
                if neighbor in model.voxels and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        if found_cone:
            print("   ISSUE: Torus and cone ARE connected! They should be separate.")
        else:
            print("   OK: Torus and cone are separate components")
    
    print("\n" + "=" * 60)
    print("SUMMARY OF ISSUES:")
    print("=" * 60)
    print("1. Torus might be too large or connecting to cone")
    print("2. Mirror operation places some voxels outside bounds (30x30x30 model)")
    print("3. Extra component likely due to mirror creating out-of-bounds voxels")
    print("=" * 60)

if __name__ == "__main__":
    analyze()
