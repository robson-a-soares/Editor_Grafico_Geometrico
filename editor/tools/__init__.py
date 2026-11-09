"""Ferramentas do editor (uma classe por ferramenta)."""

from .path_tools import FreehandTool, HandTool, PolygonTool
from .select_tool import SelectTool
from .shape_tools import EllipseTool, LineTool, NgonTool, RectTool, StarTool, TriangleTool

TOOL_CLASSES = [SelectTool, HandTool, RectTool, EllipseTool, TriangleTool, LineTool,
                PolygonTool, FreehandTool, NgonTool, StarTool]
