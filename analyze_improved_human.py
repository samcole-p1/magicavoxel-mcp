#!/usr/bin/env python3
"""Analyze the improved human character model to find issues"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from vox_utils import read_vox_file

def analyze_improved():
    """Analyze the improved human character model"""
    filepath = Path("vox") / "human_character_improved.vox"
    
    if not filepath.exists():
        print(f"Error: {filepath} not found")
        return
    
    print("=" * 60)
    print("IMPROVED HUMAN CHARACTER - DETAILED ANALYSIS")
    print("=" * 60)
    
    model = read_vox_file(filepath)
    
    print(f"\nDimensions: {model.size_x}×{model.size_y}×{model.size_z} voxels")
    print(f"Total voxels: {model.get_voxel_count()}")
    
    bounds = model.get_bounds()
    print(f"Actual bounds: {bounds[0]}×{bounds[1]}×{bounds[2]}")
    
    # Detailed proportion analysis
    print("\n" + "=" * 60)
    print("DETAILED PROPORTION ANALYSIS:")
    print("=" * 60)
    
    # Find actual ranges
    all_y = [y for (x,y,z), c in model.voxels.items() if c > 0]
    min_y = min(all_y)
    max_y = max(all_y)
    total_height = max_y - min_y + 1
    
    print(f"Total height: {total_height} voxels (from y={min_y} to y={max_y})")
    
    # Head analysis
    head_voxels = [(x,y,z) for (x,y,z), c in model.voxels.items() if y >= 28 and c > 0]
    if head_voxels:
        head_min_y = min(y for (x,y,z) in head_voxels)
        head_max_y = max(y for (x,y,z) in head_voxels)
        head_height = head_max_y - head_min_y + 1
        print(f"\nHead: y={head_min_y} to {head_max_y} ({head_height} voxels, {head_height/total_height*100:.1f}% of height)")
        print(f"  Expected: ~12.5% (4 voxels for 32-height character)")
        if head_height > 5:
            print(f"  [ISSUE] Head is {head_height - 4} voxels too tall!")
    
    # Neck analysis
    neck_voxels = [(x,y,z) for (x,y,z), c in model.voxels.items() if 26 <= y < 28 and c > 0]
    if neck_voxels:
        neck_min_y = min(y for (x,y,z) in neck_voxels)
        neck_max_y = max(y for (x,y,z) in neck_voxels)
        neck_height = neck_max_y - neck_min_y + 1
        print(f"\nNeck: y={neck_min_y} to {neck_max_y} ({neck_height} voxels)")
    else:
        print(f"\nNeck: [ISSUE] No neck voxels found at y=26-27")
    
    # Torso analysis
    torso_voxels = [(x,y,z) for (x,y,z), c in model.voxels.items() if 14 <= y < 26 and c > 0]
    if torso_voxels:
        torso_min_y = min(y for (x,y,z) in torso_voxels)
        torso_max_y = max(y for (x,y,z) in torso_voxels)
        torso_height = torso_max_y - torso_min_y + 1
        print(f"\nTorso: y={torso_min_y} to {torso_max_y} ({torso_height} voxels, {torso_height/total_height*100:.1f}% of height)")
        print(f"  Expected: ~37.5% (12 voxels for 32-height character)")
    
    # Legs analysis
    leg_voxels = [(x,y,z) for (x,y,z), c in model.voxels.items() if y < 14 and c > 0]
    if leg_voxels:
        leg_min_y = min(y for (x,y,z) in leg_voxels)
        leg_max_y = max(y for (x,y,z) in leg_voxels)
        leg_height = leg_max_y - leg_min_y + 1
        print(f"\nLegs: y={leg_min_y} to {leg_max_y} ({leg_height} voxels, {leg_height/total_height*100:.1f}% of height)")
        print(f"  Expected: ~50% (16 voxels for 32-height character)")
        if leg_height < 14:
            print(f"  [ISSUE] Legs are {16 - leg_height} voxels too short!")
    
    # Arms analysis
    arm_voxels = [(x,y,z) for (x,y,z), c in model.voxels.items() 
                  if ((x < 5 or x > 11) and 10 <= y < 24) and c > 0]
    if arm_voxels:
        arm_min_y = min(y for (x,y,z) in arm_voxels)
        arm_max_y = max(y for (x,y,z) in arm_voxels)
        arm_height = arm_max_y - arm_min_y + 1
        print(f"\nArms: y={arm_min_y} to {arm_max_y} ({arm_height} voxels)")
        print(f"  Expected: ~12 voxels (from shoulder to mid-thigh)")
    
    # Check for issues
    print("\n" + "=" * 60)
    print("ISSUES FOUND:")
    print("=" * 60)
    
    issues = []
    
    # Check head size
    if head_voxels:
        head_height = max(y for (x,y,z) in head_voxels) - min(y for (x,y,z) in head_voxels) + 1
        if head_height > 4:
            issues.append(f"Head too large: {head_height} voxels (should be ~4)")
    
    # Check if head overlaps with torso
    head_bottom = min(y for (x,y,z) in head_voxels) if head_voxels else 999
    torso_top = max(y for (x,y,z) in torso_voxels) if torso_voxels else -1
    if head_bottom <= torso_top:
        issues.append(f"Head overlaps with torso! Head bottom (y={head_bottom}) <= Torso top (y={torso_top})")
    
    # Check leg length
    if leg_voxels:
        leg_height = max(y for (x,y,z) in leg_voxels) - min(y for (x,y,z) in leg_voxels) + 1
        if leg_height < 15:
            issues.append(f"Legs too short: {leg_height} voxels (should be ~16)")
    
    # Check if hands are properly placed
    hand_voxels = [(x,y,z) for (x,y,z), c in model.voxels.items() 
                   if ((x < 5 or x > 11) and y <= 12 and c == 1)]
    if not hand_voxels:
        issues.append("No hands found (should have skin-colored blocks at end of arms)")
    elif len(hand_voxels) < 10:
        issues.append(f"Hands too small: only {len(hand_voxels)} voxels")
    
    # Check if feet are properly placed
    foot_voxels = [(x,y,z) for (x,y,z), c in model.voxels.items() 
                   if y <= 1 and c == 6]
    if not foot_voxels:
        issues.append("No feet/shoes found (should have gray blocks at y=0-1)")
    elif len(foot_voxels) < 10:
        issues.append(f"Feet too small: only {len(foot_voxels)} voxels")
    
    # Check symmetry
    center_x = model.size_x // 2
    symmetry_issues = 0
    for (x, y, z), color in list(model.voxels.items())[:100]:  # Sample
        if x < center_x:
            mirror_x = 2 * center_x - x
            if (mirror_x, y, z) not in model.voxels:
                symmetry_issues += 1
                if symmetry_issues == 1:
                    issues.append(f"Symmetry issue: Missing mirror at ({mirror_x},{y},{z}) for ({x},{y},{z})")
    
    # Check for disconnected parts
    components = model.find_connected_components()
    if len(components) > 1:
        issues.append(f"Model has {len(components)} disconnected pieces (should be 1)")
        for i, comp in enumerate(components, 1):
            b = comp['bounds']
            issues.append(f"  Component {i}: {comp['voxel_count']} voxels at ({b['min_x']},{b['min_y']},{b['min_z']})")
    
    # Check for gaps
    if head_voxels and torso_voxels:
        head_bottom = min(y for (x,y,z) in head_voxels)
        torso_top = max(y for (x,y,z) in torso_voxels)
        gap = head_bottom - torso_top - 1
        if gap > 1:
            issues.append(f"Gap between head and torso: {gap} voxels (head bottom y={head_bottom}, torso top y={torso_top})")
        elif gap < 0:
            issues.append(f"Head overlaps torso by {abs(gap)} voxels!")
    
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
    else:
        print("No major issues found!")
    
    # Visual structure check
    print("\n" + "=" * 60)
    print("VISUAL STRUCTURE CHECK:")
    print("=" * 60)
    
    # Check head shape
    head_x_range = set(x for (x,y,z) in head_voxels)
    head_z_range = set(z for (x,y,z) in head_voxels)
    print(f"Head spans: X={min(head_x_range)}-{max(head_x_range)}, Z={min(head_z_range)}-{max(head_z_range)}")
    
    # Check torso width at shoulders vs waist
    if torso_voxels:
        shoulder_y = max(y for (x,y,z) in torso_voxels)
        waist_y = min(y for (x,y,z) in torso_voxels) + (max(y for (x,y,z) in torso_voxels) - min(y for (x,y,z) in torso_voxels)) // 2
        
        shoulder_width = len(set(x for (x,y,z) in torso_voxels if y == shoulder_y))
        waist_width = len(set(x for (x,y,z) in torso_voxels if y == waist_y))
        print(f"Torso: Shoulder width={shoulder_width}, Waist width={waist_width}")
        if shoulder_width <= waist_width:
            print("  [ISSUE] Shoulders should be wider than waist!")
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    analyze_improved()
