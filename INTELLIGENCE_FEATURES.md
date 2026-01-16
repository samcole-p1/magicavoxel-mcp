# MCP Server Intelligence Features

## Overview

The MagicaVoxel MCP server now includes an intelligence layer that makes it smarter and more user-friendly. The intelligence system provides context awareness, smart defaults, pattern recognition, and learning capabilities.

## Key Intelligence Features

### 1. **Context Awareness**
- **Operation Tracking**: Remembers all operations you perform
- **Model History**: Tracks which models you've worked with
- **Pattern Learning**: Learns from your common operations
- **Smart Suggestions**: Suggests next steps based on current model state

### 2. **Smart Defaults**
- **Automatic Sizing**: Suggests reasonable dimensions based on context
- **Position Suggestions**: Recommends center positions for shapes
- **Template Support**: Pre-built templates for common objects
- **Validation**: Prevents errors before they happen

### 3. **Templates System**
Available templates:
- **character**: Standard game character (16x32x16)
- **warrior**: Warrior with armor (20x40x20)
- **building**: Building structure (32x32x32)
- **tree**: Simple tree (8x16x8)

### 4. **Color Presets**
Material-based color suggestions:
- `skin` → RGB(255, 220, 180)
- `armor` → RGB(140, 140, 150)
- `red_cloth` → RGB(220, 60, 60)
- `brown_hair` → RGB(120, 70, 30)
- `dark_boots` → RGB(60, 40, 25)
- `bronze` → RGB(180, 120, 60)
- `stone` → RGB(150, 150, 150)
- `wood` → RGB(139, 90, 43)
- `grass` → RGB(34, 139, 34)
- `water` → RGB(30, 144, 255)

## New Smart Tools

### `smart_create_model`
Intelligently create models with template support:
```
"Create a warrior model using the warrior template"
"Create a character model with smart defaults"
```

**Features:**
- Uses templates for standard dimensions
- Validates dimensions before creation
- Suggests next operations
- Tracks operation for learning

### `get_suggestions`
Get intelligent suggestions for a model:
```
"Get suggestions for my_warrior model"
```

**Returns:**
- Next recommended operations
- Based on current model state
- Context-aware suggestions

### `list_templates`
List all available templates:
```
"List available templates"
```

### `get_operation_stats`
Get statistics about your usage:
```
"Show me operation statistics"
```

**Shows:**
- Most used operations
- Operation frequency
- Usage patterns

## Enhanced Existing Tools

All existing tools now have intelligence features:

### **Validation**
- Checks dimensions before operations
- Prevents out-of-bounds errors
- Suggests fixes for invalid parameters

### **Operation Tracking**
- All operations are tracked
- Used for learning and suggestions
- Helps improve defaults over time

### **Smart Suggestions**
- After creating models, suggests next steps
- Context-aware recommendations
- Based on model state

## Usage Examples

### Using Templates
```
"Create a warrior model using the warrior template"
→ Creates 20x40x20 model with warrior proportions
```

### Getting Suggestions
```
"Get suggestions for game_warrior"
→ Returns: "Model is empty - consider adding shapes..."
```

### Smart Defaults
```
"Create a model called my_character"
→ Uses smart defaults (16x32x16) for character
→ Suggests: "Try: create_sphere, create_cylinder, or fill_box"
```

### Operation Statistics
```
"Show operation statistics"
→ Shows: "create_voxel_model: 5 times"
         "create_sphere: 3 times"
```

## How Intelligence Works

### 1. **Context File**
Stores context in `.mcp_context.json`:
- Recent models
- Operation history
- User preferences
- Common patterns

### 2. **Learning System**
- Tracks all operations
- Learns common patterns
- Improves suggestions over time
- Remembers your preferences

### 3. **Validation System**
- Checks parameters before execution
- Prevents common errors
- Suggests corrections
- Ensures compatibility

### 4. **Template System**
- Pre-built configurations
- Standard game asset sizes
- Easy to extend
- Customizable

## Benefits

1. **Fewer Errors**: Validation prevents mistakes
2. **Faster Workflow**: Smart defaults save time
3. **Better Results**: Templates ensure proper proportions
4. **Learning System**: Gets smarter with use
5. **Context Awareness**: Remembers your work

## Future Enhancements

Potential additions:
- **AI Integration**: Natural language understanding
- **Pattern Recognition**: Auto-detect common structures
- **Auto-completion**: Suggest completions for partial commands
- **Multi-model Context**: Understand relationships between models
- **Style Learning**: Learn your preferred styles and colors

## Technical Details

### Files
- `intelligence.py`: Core intelligence layer
- `smart_tools.py`: Smart tool wrappers
- `.mcp_context.json`: Context storage (auto-generated)

### Dependencies
- No external dependencies required
- Pure Python implementation
- Lightweight and fast

### Performance
- Minimal overhead
- Context file is small
- Fast lookups and suggestions