# Test Model Visual Description

## Overview
The `test_model.vox` is a 30×30×30 voxel model that demonstrates all 15 new tools. It contains multiple disconnected components (7 total) showing various shapes and transformations.

## Layout by Region

### Lower Left Corner (Origin Area)
- **Partially Cleared Box (Color 1 - Red)**
  - Original box from (5,5,5) to (10,10,10)
  - Has a single voxel removed at (7,7,7) - creating a small hole
  - Then region (5,5,5) to (8,8,8) was cleared - removing the front-left portion
  - Result: A box with missing front-left corner section

- **Mirrored Cubes (Color 5 - Magenta)**
  - Original cube: 4×4×4 cube at (0,0,0) to (3,3,3)
  - Mirrored copy: Same cube mirrored across x=15 plane, appearing at (27,0,0) to (30,3,3)
  - Result: Two identical cubes on opposite sides of the model

- **Extruded Column (Color 8 - Custom)**
  - Base: 3×1×3 platform at y=10, from (0,10,0) to (2,10,2)
  - Extruded upward 5 units in +Y direction
  - Result: A vertical column/pillar 3×6×3 voxels tall, standing on the base

### Center Area
- **Large Torus/Donut (Color 2 - Green)**
  - Centered at (15, 15, 15)
  - Major radius: 8 voxels (distance from center to tube center)
  - Minor radius: 3 voxels (thickness of the tube)
  - Axis: Y (vertical orientation)
  - Result: A large vertical donut shape in the center of the model

- **Cone (Color 3 - Blue)**
  - Base center: (15, 0, 15) - at the bottom center
  - Base radius: 5 voxels
  - Height: 10 voxels
  - Axis: Y (pointing upward)
  - Result: A cone sitting on the bottom, pointing upward toward the torus

### Right Side
- **Rotated Box (Color 4 - Yellow)**
  - Original: 3×3×3 box at (20,5,5) to (22,7,7)
  - Rotated 90° around Y axis, centered at (21,6,6)
  - Result: The box appears rotated, maintaining its position but with different orientation

- **Moved Box (Color 6 - Cyan)**
  - Original position: 3×3×3 box at (25,0,0) to (27,2,2)
  - Moved to: (25,5,0) to (27,7,2)
  - Result: Same box shape, but lifted 5 units upward

## Color Legend
- **Color 1 (Red)**: Partially cleared box
- **Color 2 (Green)**: Torus
- **Color 3 (Blue)**: Cone
- **Color 4 (Yellow)**: Rotated box
- **Color 5 (Magenta)**: Mirrored cubes
- **Color 6 (Cyan)**: Moved box
- **Color 7**: (Used in test_model_2 for sphere)
- **Color 8**: Extruded column

## Component Breakdown (7 Separate Pieces)

1. **Large Component (1348 voxels)**: The torus and cone, likely connected or very close
2. **Medium Component (278 voxels)**: The partially cleared box
3. **Small Component (152 voxels)**: One of the smaller structures
4. **4 Additional Small Components**: Various isolated boxes and shapes

## Spatial Relationships

```
Top View (looking down Y axis):
┌─────────────────────────────────┐
│ Mirrored Cube    │    Rotated   │
│ (Magenta)        │    Box       │
│                  │    (Yellow)  │
│                  │              │
│                  │    Torus     │
│                  │    (Green)   │
│                  │              │
│ Extruded         │    Moved     │
│ Column           │    Box       │
│ (Color 8)        │    (Cyan)   │
│                  │              │
│ Partially        │    Cone      │
│ Cleared Box      │    (Blue)    │
│ (Red)            │              │
└─────────────────────────────────┘
```

## Key Features to Look For

1. **Hole in Box**: The red box should have a missing voxel at (7,7,7) and a cleared corner section
2. **Symmetry**: Two identical magenta cubes on opposite sides (mirror operation)
3. **Vertical Donut**: Large green torus in the center, oriented vertically
4. **Pointed Cone**: Blue cone at bottom center, pointing up
5. **Rotated Shape**: Yellow box that appears rotated from its original orientation
6. **Elevated Box**: Cyan box that's been moved upward
7. **Tall Column**: Vertical column created by extrusion operation

## Statistics
- **Total Voxels**: 2005
- **Surface Voxels**: 1219 (60.8% - most voxels are exposed)
- **Connected Components**: 7 separate pieces
- **Dimensions**: 30×30×30 voxels

## What This Demonstrates

This model showcases:
- ✅ Basic operations (place, remove, clear)
- ✅ Complex shapes (torus, cone)
- ✅ Transformations (rotate, mirror, move, extrude)
- ✅ Multiple disconnected components
- ✅ Various colors and shapes working together

The model is intentionally fragmented to demonstrate that the analysis tools can correctly identify separate connected components.
