# Excalidraw Dark Mode for System Architecture Diagrams

This reference extends `references/dark-mode.md` with a production-tested pattern for multi-layer system architecture diagrams (like ONEBOT 3.0's 7-layer quant stack).

## Background Zone Strategy

For layered architectures, use **nested background rectangles** with low opacity:

```json
{
  "type": "rectangle", "id": "bg_layer1",
  "x": 220, "y": 140, "width": 900, "height": 120,
  "roundness": { "type": 3 },
  "backgroundColor": "#5c3d1a",
  "fillStyle": "solid",
  "strokeColor": "#f59e0b",
  "strokeWidth": 2,
  "opacity": 30
}
```

**Opacity rules:**
- Layer boundaries: **30-35** (visible but not overwhelming)
- Component fills: **solid 100** (use dark variants from below)
- Never exceed 40 opacity for zones — components become unreadable

## Semantic Color Mapping for System Architecture

When diagramming software systems with multiple layers, map layers to colors consistently:

| Layer Type | Zone Fill | Component Fill | Stroke | Example |
|-----------|-----------|----------------|--------|---------|
| Data / External | `#5c3d1a` (amber zone) | `#2d1a00` | `#f59e0b` | APIs, feeds |
| Prediction / ML | `#1a4d2e` (green zone) | `#0f3d22` | `#22c55e` | Models, ensemble |
| Analysis | `#2d1b69` (purple zone) | `#241447` | `#8b5cf6` | Greeks, sentiment |
| Arbitration / Security | `#5c1a1a` (red zone) | `#3d0f1a` | `#ef4444` | Dispute resolution |
| Backtest / Validation | `#5c3d1a` (orange zone) | `#3d2600` | `#f59e0b` | Historical engine |
| Backup / Infrastructure | `#1e3a5f` (blue zone) | `#1e293b` | `#4a9eed` | Snapshot, recovery |
| LLM / AI | `#1a4d4d` (teal zone) | `#0f2d3d` | `#06b6d4` | DeepSeek, GPT |
| Orchestrator | `#2d1b69` (purple) | `#1e0f00` | `#f59e0b` | core.py |

## Layer Label Convention

Place labels **inside the zone** at top-left, 10px from edge:

```json
{
  "type": "text", "id": "l1_label",
  "x": 240, "y": 150,
  "text": "Layer 1 — Data Layers",
  "fontSize": 18, "fontFamily": 1,
  "strokeColor": "#f59e0b"
}
```

## Component + Label Pair Pattern

Every component needs a bound text element immediately following it:

```json
[
  {
    "type": "rectangle", "id": "comp1",
    "x": 280, "y": 185, "width": 120, "height": 60,
    "roundness": { "type": 3 },
    "backgroundColor": "#2d1a00",
    "fillStyle": "solid",
    "strokeColor": "#f59e0b",
    "strokeWidth": 2,
    "boundElements": [{ "id": "t_comp1", "type": "text" }]
  },
  {
    "type": "text", "id": "t_comp1",
    "x": 285, "y": 195, "width": 110, "height": 40,
    "text": "Tradier\nOptions",
    "fontSize": 16, "fontFamily": 1,
    "strokeColor": "#e5e5e5",
    "textAlign": "center", "verticalAlign": "middle",
    "containerId": "comp1", "originalText": "Tradier\nOptions",
    "autoResize": true
  }
]
```

## Arrow Conventions

**Vertical flow arrows** (layer to layer):
```json
{
  "type": "arrow", "id": "a_l1_l2",
  "x": 650, "y": 260, "width": 0, "height": 75,
  "points": [[0,0],[0,75]],
  "endArrowhead": "arrow",
  "strokeColor": "#22c55e",
  "strokeWidth": 2,
  "boundElements": [{ "id": "t_a_l1l2", "type": "text" }]
}
```

**Diagonal arrows** (split flow):
```json
{
  "type": "arrow", "id": "a_split",
  "x": 450, "y": 545, "width": -50, "height": 90,
  "points": [[0,0],[-50,90]],
  "endArrowhead": "arrow",
  "strokeColor": "#ef4444",
  "strokeWidth": 2
}
```

## Full Example: ONEBOT 3.0

See `/tmp/onebot_excalidraw_skill.excalidraw` for a complete 7-layer quant trading architecture with:
- 6 data source components
- 4 prediction models
- 6 analysis engines
- 2 arbitration modules
- 2 backtest engines
- 2 backup modules
- 2 LLM providers
- 1 core orchestrator
- 1 output node

All using the dark mode palette above with consistent semantic coloring.
