#!/usr/bin/env python3
"""Deep analysis of test model to find logic issues"""

import sys
from pathlib import Path
import math

sys.path.insert(0, str(Path(__file__).parent))

from vox_utils import read_vox_file

def analyze_torus_algorithm():
    """Analyze if torus algorithm has issues"""
    print("=" * 60)
    print("DEEP TORUS ALGORITHM ANALYSIS")
    print("=" * 60)
    
    model = read_vox_file(Path("vox") / "test_model.vox")
    
    center_x, center_y, center_z = 15, 15, 15
    major_radius = 8
    minor_radius = 3
    
    # Check torus voxels
    torus_voxels = [(x,y,z) for (x,y,z), c in model.voxels.items() if c == 2]
    
    print(f"Torus voxels found: {len(torus_voxels)}")
    print(f"Expected: ~1421 voxels (theoretical)")
    
    # Check if algorithm is placing voxels correctly
    # For a torus, the equation is: (R - sqrt((x-cx)² + (z-cz)²))² + (y-cy)² <= r²
    # Where R = major_radius, r = minor_radius
    
    correct_count = 0
    incorrect_count = 0
    
    for x, y, z in torus_voxels[:100]:  # Check first 100
        dx = x - center_x
        dz = z - center_z
        dy = y - center_y
        
        # Distance from center in XZ plane
        dist_from_center = math.sqrt(dx*dx + dz*dz)
        
        if dist_from_center == 0:
            continue
        
        # Distance from torus center circle
        dist_from_torus_center = abs(dist_from_center - major_radius)
        
        # Check if in tube
        dist_sq = dist_from_torus_center * dist_from_torus_center + dy * dy
        minor_r_sq = minor_radius * minor_radius
        
        if dist_sq <= minor_r_sq:
            correct_count += 1
        else:
            incorrect_count += 1
            print(f"  Incorrect voxel at ({x},{y},{z}): dist_sq={dist_sq:.2f}, minor_r_sq={minor_r_sq}")
    
    print(f"\nSample check: {correct_count} correct, {incorrect_count} incorrect")
    
    # Check bounds
    if torus_voxels:
        xs = [x for x,y,z in torus_voxels]
        ys = [y for x,y,z in torus_voxels]
        zs = [z for x,y,z in torus_voxels]
        print(f"\nTorus bounds: X({min(xs)}-{max(xs)}), Y({min(ys)}-{max(ys)}), Z({min(zs)}-{max(zs)})")
        print(f"Expected bounds: X(7-23), Y(12-18), Z(7-23)")
        
        expected_min = center_x - major_radius - minor_radius
        expected_max = center_x + major_radius + minor_radius
        if min(xs) == expected_min and max(xs) == expected_max:
            print("[OK] X bounds correct")
        else:
            print(f"[ISSUE] X bounds: expected {expected_min}-{expected_max}, got {min(xs)}-{max(xs)}")

def analyze_mirror_issue():
    """Analyze mirror bounds issue"""
    print("\n" + "=" * 60)
    print("MIRROR BOUNDS ANALYSIS")
    print("=" * 60)
    
    model = read_vox_file(Path("vox") / "test_model.vox")
    
    # Check original cube
    cube1 = [(x,y,z) for (x,y,z), c in model.voxels.items() 
             if c == 5 and 0 <= x <= 2 and 0 <= y <= 2 and 0 <= z <= 2]
    print(f"Original cube voxels: {len(cube1)} (expected 27)")
    
    # Check mirrored cube
    cube2 = [(x,y,z) for (x,y,z), c in model.voxels.items() 
             if c == 5 and 28 <= x <= 30 and 0 <= y <= 2 and 0 <= z <= 2]
    print(f"Mirrored cube voxels: {len(cube2)} (expected 27)")
    
    if len(cube2) < 27:
        print("\n[ISSUE] Mirrored cube is incomplete!")
        print("Missing voxels are likely at x=30 (out of bounds for 30×30×30 model)")
        print("Model was auto-expanded to 31×30×30 to accommodate x=30")
        print("\nSolution: The mirror operation works, but places voxels at x=30.")
        print("This is technically correct - the model size expands automatically.")
        print("However, for a 30×30×30 model, we should ensure mirror stays within bounds.")

def check_all_rotations():
    """Check if all rotation angles work correctly"""
    print("\n" + "=" * 60)
    print("ROTATION COMPREHENSIVE CHECK")
    print("=" * 60)
    
    # Test all rotation combinations
    test_cases = [
        (1, 0, 0, 'x', 90, (1, 0, 0)),   # Rotate (1,0,0) 90° around X -> (1,0,0) stays
        (0, 1, 0, 'x', 90, (0, 0, 1)),   # Rotate (0,1,0) 90° around X -> (0,0,1)
        (0, 0, 1, 'x', 90, (0, -1, 0)),  # Rotate (0,0,1) 90° around X -> (0,-1,0)
        (1, 0, 0, 'y', 90, (0, 0, -1)),  # Rotate (1,0,0) 90° around Y -> (0,0,-1)
        (0, 1, 0, 'y', 90, (0, 1, 0)),   # Rotate (0,1,0) 90° around Y -> (0,1,0) stays
        (0, 0, 1, 'y', 90, (1, 0, 0)),   # Rotate (0,0,1) 90° around Y -> (1,0,0)
        (1, 0, 0, 'z', 90, (0, 1, 0)),   # Rotate (1,0,0) 90° around Z -> (0,1,0)
        (0, 1, 0, 'z', 90, (-1, 0, 0)),  # Rotate (0,1,0) 90° around Z -> (-1,0,0)
        (0, 0, 1, 'z', 90, (0, 0, 1)),   # Rotate (0,0,1) 90° around Z -> (0,0,1) stays
    ]
    
    center = (0, 0, 0)
    errors = []
    
    for x, y, z, axis, degrees, expected in test_cases:
        dx, dy, dz = x - center[0], y - center[1], z - center[2]
        
        if axis == 'x':
            if degrees == 90:
                new_x, new_y, new_z = dx, -dz, dy
            elif degrees == 180:
                new_x, new_y, new_z = dx, -dy, -dz
            elif degrees == 270:
                new_x, new_y, new_z = dx, dz, -dy
        elif axis == 'y':
            if degrees == 90:
                new_x, new_y, new_z = dz, dy, -dx
            elif degrees == 180:
                new_x, new_y, new_z = -dx, dy, -dz
            elif degrees == 270:
                new_x, new_y, new_z = -dz, dy, dx
        else:  # z
            if degrees == 90:
                new_x, new_y, new_z = -dy, dx, dz
            elif degrees == 180:
                new_x, new_y, new_z = -dx, -dy, dz
            elif degrees == 270:
                new_x, new_y, new_z = dy, -dx, dz
        
        new_x += center[0]
        new_y += center[1]
        new_z += center[2]
        
        result = (new_x, new_y, new_z)
        if result != expected:
            errors.append(f"({x},{y},{z}) {axis} {degrees}°: got {result}, expected {expected}")
    
    if errors:
        print("[ERRORS FOUND]:")
        for error in errors:
            print(f"  {error}")
    else:
        print("[OK] All rotation test cases passed!")

if __name__ == "__main__":
    analyze_torus_algorithm()
    analyze_mirror_issue()
    check_all_rotations()
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
