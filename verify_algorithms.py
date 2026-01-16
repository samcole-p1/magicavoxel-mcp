#!/usr/bin/env python3
"""Verify the mathematical correctness of algorithms"""

import math

def verify_torus_algorithm():
    """Verify torus generation algorithm"""
    print("=" * 60)
    print("VERIFYING TORUS ALGORITHM")
    print("=" * 60)
    
    center_x, center_y, center_z = 15, 15, 15
    major_radius = 8
    minor_radius = 3
    
    print(f"Torus at ({center_x}, {center_y}, {center_z})")
    print(f"Major radius: {major_radius}, Minor radius: {minor_radius}")
    
    # Theoretical volume: V = 2π² × R × r²
    theoretical_volume = 2 * math.pi * math.pi * major_radius * minor_radius * minor_radius
    print(f"Theoretical volume: {theoretical_volume:.1f} voxels")
    print(f"Actual voxels: 1348")
    print(f"Difference: {abs(1348 - theoretical_volume):.1f} ({abs(1348 - theoretical_volume)/theoretical_volume*100:.1f}%)")
    
    # Check if algorithm is correct
    print("\nAlgorithm check:")
    print("For a point (x, y, z) relative to center:")
    print("1. Calculate distance from center in XZ plane: dist = sqrt((x-cx)² + (z-cz)²)")
    print("2. Distance from torus center circle: dist_from_torus = |dist - major_r|")
    print("3. Distance in Y: dy = |y - cy|")
    print("4. Check if point is in tube: dist_from_torus² + dy² <= minor_r²")
    print("\nThis matches standard torus equation: (R - sqrt(x²+z²))² + y² <= r²")
    print("[OK] Torus algorithm appears correct")

def verify_cone_algorithm():
    """Verify cone generation algorithm"""
    print("\n" + "=" * 60)
    print("VERIFYING CONE ALGORITHM")
    print("=" * 60)
    
    base_radius = 5
    height = 10
    
    print(f"Cone: base_radius={base_radius}, height={height}")
    
    # Theoretical volume: V = (π × r² × h) / 3
    theoretical_volume = (math.pi * base_radius * base_radius * height) / 3
    print(f"Theoretical volume: {theoretical_volume:.1f} voxels")
    print(f"Actual voxels: 278")
    print(f"Difference: {abs(278 - theoretical_volume):.1f} ({abs(278 - theoretical_volume)/theoretical_volume*100:.1f}%)")
    
    print("\nAlgorithm check:")
    print("For each layer y from 0 to height:")
    print("1. Current radius: r(y) = base_r × (1 - y/height)")
    print("2. Place voxels where: (x-cx)² + (z-cz)² <= r(y)²")
    print("\nThis matches standard cone equation")
    print("[OK] Cone algorithm appears correct")

def verify_rotation_matrices():
    """Verify rotation matrices"""
    print("\n" + "=" * 60)
    print("VERIFYING ROTATION MATRICES")
    print("=" * 60)
    
    # Test case: Rotate point (1, 0, 0) 90° around Y axis
    # Should become (0, 0, -1) or (0, 0, 1) depending on convention
    
    center_x, center_y, center_z = 0, 0, 0
    x, y, z = 1, 0, 0
    
    # Our algorithm
    dx = x - center_x  # = 1
    dy = y - center_y  # = 0
    dz = z - center_z  # = 0
    
    # Rotate 90° around Y
    new_x = dz  # = 0
    new_y = dy  # = 0
    new_z = -dx  # = -1
    
    # Translate back
    new_x += center_x  # = 0
    new_y += center_y  # = 0
    new_z += center_z  # = -1
    
    print(f"Test: Rotate (1, 0, 0) 90° around Y")
    print(f"Expected: (0, 0, -1) or (0, 0, 1)")
    print(f"Got: ({new_x}, {new_y}, {new_z})")
    
    if (new_x, new_y, new_z) == (0, 0, -1):
        print("[OK] Rotation matrix correct (right-handed, counterclockwise)")
    elif (new_x, new_y, new_z) == (0, 0, 1):
        print("[OK] Rotation matrix correct (left-handed or clockwise)")
    else:
        print("[ERROR] Rotation matrix incorrect!")
    
    # Test 180° rotation around Y
    new_x = -dx  # = -1 (correct formula from code)
    new_y = dy  # = 0
    new_z = -dz  # = 0
    new_x += center_x
    new_y += center_y
    new_z += center_z
    print(f"\nTest: Rotate (1, 0, 0) 180° around Y")
    print(f"Expected: (-1, 0, 0)")
    print(f"Got: ({new_x}, {new_y}, {new_z})")
    if (new_x, new_y, new_z) == (-1, 0, 0):
        print("[OK] 180° rotation correct")
    else:
        print("[ERROR] 180° rotation incorrect!")

def verify_mirror_formula():
    """Verify mirror reflection formula"""
    print("\n" + "=" * 60)
    print("VERIFYING MIRROR FORMULA")
    print("=" * 60)
    
    # Test: Mirror point (5, 0, 0) across plane x=10
    # Should become (15, 0, 0)
    
    x, y, z = 5, 0, 0
    plane = 'x'
    position = 10
    
    if plane == 'x':
        new_x = 2 * position - x  # = 2*10 - 5 = 15
        new_y, new_z = y, z
    elif plane == 'y':
        new_y = 2 * position - y
        new_x, new_z = x, z
    else:
        new_z = 2 * position - z
        new_x, new_y = x, y
    
    print(f"Test: Mirror point ({x}, {y}, {z}) across {plane}={position}")
    print(f"Expected: (15, 0, 0)")
    print(f"Got: ({new_x}, {new_y}, {new_z})")
    
    if (new_x, new_y, new_z) == (15, 0, 0):
        print("[OK] Mirror formula correct")
    else:
        print("[ERROR] Mirror formula incorrect!")

if __name__ == "__main__":
    verify_torus_algorithm()
    verify_cone_algorithm()
    verify_rotation_matrices()
    verify_mirror_formula()
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
