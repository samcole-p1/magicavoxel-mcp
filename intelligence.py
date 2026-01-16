#!/usr/bin/env python3
"""
Intelligence layer for MagicaVoxel MCP Server
Adds context awareness, smart defaults, pattern recognition, and templates
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime

class MCPIntelligence:
    """Intelligent assistant for MCP operations"""
    
    def __init__(self, vox_dir: Path):
        self.vox_dir = vox_dir
        self.context_file = Path(__file__).parent / ".mcp_context.json"
        self.context = self._load_context()
        
        # Common patterns and templates
        self.templates = self._load_templates()
        self.color_presets = self._load_color_presets()
        
    def _load_context(self) -> Dict:
        """Load context from file"""
        if self.context_file.exists():
            try:
                with open(self.context_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "recent_models": [],
            "common_operations": {},
            "user_preferences": {},
            "model_history": []
        }
    
    def _save_context(self):
        """Save context to file"""
        try:
            with open(self.context_file, 'w') as f:
                json.dump(self.context, f, indent=2)
        except:
            pass
    
    def _load_templates(self) -> Dict:
        """Load common templates"""
        return {
            "character": {
                "description": "Standard game character proportions",
                "dimensions": (16, 32, 16),
                "components": ["head", "torso", "arms", "legs"]
            },
            "warrior": {
                "description": "Warrior character with armor",
                "dimensions": (20, 40, 20),
                "components": ["head", "helmet", "armor_torso", "arms", "legs", "boots"]
            },
            "building": {
                "description": "Standard building structure",
                "dimensions": (32, 32, 32),
                "components": ["walls", "roof", "door", "windows"]
            },
            "tree": {
                "description": "Simple tree structure",
                "dimensions": (8, 16, 8),
                "components": ["trunk", "leaves"]
            }
        }
    
    def _load_color_presets(self) -> Dict:
        """Load color presets for common materials"""
        return {
            "skin": {"r": 255, "g": 220, "b": 180},
            "armor": {"r": 140, "g": 140, "b": 150},
            "red_cloth": {"r": 220, "g": 60, "b": 60},
            "brown_hair": {"r": 120, "g": 70, "b": 30},
            "dark_boots": {"r": 60, "g": 40, "b": 25},
            "bronze": {"r": 180, "g": 120, "b": 60},
            "stone": {"r": 150, "g": 150, "b": 150},
            "wood": {"r": 139, "g": 90, "b": 43},
            "grass": {"r": 34, "g": 139, "b": 34},
            "water": {"r": 30, "g": 144, "b": 255}
        }
    
    def track_operation(self, operation: str, model_name: str, details: Dict):
        """Track operations for learning"""
        if "model_history" not in self.context:
            self.context["model_history"] = []
        
        self.context["model_history"].append({
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "model": model_name,
            "details": details
        })
        
        # Keep only last 100 operations
        if len(self.context["model_history"]) > 100:
            self.context["model_history"] = self.context["model_history"][-100:]
        
        self._save_context()
    
    def get_smart_defaults(self, operation: str, model_name: Optional[str] = None) -> Dict:
        """Get smart defaults based on context and operation type"""
        defaults = {}
        
        if operation == "create_voxel_model":
            # Check if similar models exist
            if model_name:
                similar = self._find_similar_models(model_name)
                if similar:
                    # Use dimensions from similar model
                    defaults["suggested_dimensions"] = similar.get("dimensions")
        
        elif operation == "create_sphere":
            # Suggest reasonable radius based on model size
            if model_name:
                model_info = self._get_model_info(model_name)
                if model_info:
                    max_dim = max(model_info["dimensions"].values())
                    defaults["suggested_radius"] = max(3, min(10, max_dim // 4))
        
        elif operation == "place_voxel":
            # Suggest center of model
            if model_name:
                model_info = self._get_model_info(model_name)
                if model_info:
                    dims = model_info["dimensions"]
                    defaults["suggested_position"] = (
                        dims["x"] // 2,
                        dims["y"] // 2,
                        dims["z"] // 2
                    )
        
        return defaults
    
    def suggest_color(self, material: str) -> Optional[Tuple[int, int, int]]:
        """Suggest color for a material"""
        if material.lower() in self.color_presets:
            preset = self.color_presets[material.lower()]
            return (preset["r"], preset["g"], preset["b"])
        return None
    
    def get_template(self, template_name: str) -> Optional[Dict]:
        """Get a template by name"""
        return self.templates.get(template_name.lower())
    
    def list_templates(self) -> List[str]:
        """List available templates"""
        return list(self.templates.keys())
    
    def _find_similar_models(self, model_name: str) -> Optional[Dict]:
        """Find similar models in history"""
        # Simple similarity: check if name contains common words
        for entry in reversed(self.context.get("model_history", [])):
            if entry["model"] != model_name:
                # Check for similar operations
                if entry["operation"] == "create_voxel_model":
                    return entry.get("details", {})
        return None
    
    def _get_model_info(self, model_name: str) -> Optional[Dict]:
        """Get information about a model"""
        model_path = self.vox_dir / f"{model_name}.vox"
        if not model_path.exists():
            model_path = self.vox_dir / model_name
            if not model_path.exists():
                return None
        
        try:
            from vox_utils import read_vox_file
            model = read_vox_file(model_path)
            return {
                "dimensions": {
                    "x": model.size_x,
                    "y": model.size_y,
                    "z": model.size_z
                },
                "voxel_count": model.get_voxel_count()
            }
        except:
            return None
    
    def suggest_next_operations(self, model_name: str) -> List[str]:
        """Suggest next operations based on current model state"""
        suggestions = []
        
        model_info = self._get_model_info(model_name)
        if not model_info:
            suggestions.append("First, create the model using create_voxel_model")
            return suggestions
        
        voxel_count = model_info.get("voxel_count", 0)
        
        if voxel_count == 0:
            suggestions.append("Model is empty - consider adding shapes or filling regions")
            suggestions.append("Try: create_sphere, create_cylinder, or fill_box")
        elif voxel_count < 100:
            suggestions.append("Model is small - consider adding more details")
            suggestions.append("Try: create_pyramid, create_stairs, or copy_region")
        else:
            suggestions.append("Model has content - consider adding details or modifying colors")
            suggestions.append("Try: replace_color, set_palette_color, or copy_region")
        
        return suggestions
    
    def validate_operation(self, operation: str, params: Dict, model_name: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Validate operation parameters and suggest fixes"""
        if operation == "create_voxel_model":
            width = params.get("width", 10)
            height = params.get("height", 10)
            depth = params.get("depth", 10)
            
            if width > 256 or height > 256 or depth > 256:
                return False, f"Dimensions exceed MagicaVoxel limit of 256. Suggested: {min(256, width)}x{min(256, height)}x{min(256, depth)}"
        
        elif operation in ["create_sphere", "create_cylinder"]:
            if model_name:
                model_info = self._get_model_info(model_name)
                if model_info:
                    dims = model_info["dimensions"]
                    radius = params.get("radius", 0)
                    center_x = params.get("center_x", 0)
                    center_y = params.get("center_y", 0)
                    center_z = params.get("center_z", 0)
                    
                    if center_x + radius > dims["x"] or center_x - radius < 0:
                        return False, f"Sphere extends beyond model bounds in X. Model width: {dims['x']}"
                    if center_y + radius > dims["y"] or center_y - radius < 0:
                        return False, f"Sphere extends beyond model bounds in Y. Model height: {dims['y']}"
                    if center_z + radius > dims["z"] or center_z - radius < 0:
                        return False, f"Sphere extends beyond model bounds in Z. Model depth: {dims['z']}"
        
        return True, None
    
    def get_operation_stats(self) -> Dict:
        """Get statistics about operations"""
        stats = defaultdict(int)
        for entry in self.context.get("model_history", []):
            stats[entry["operation"]] += 1
        return dict(stats)