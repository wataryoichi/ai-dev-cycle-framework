# Claude Implementation Summary

## What Was Done

Both review findings are fixed:

1. **Rotation drift** — Pieces now store a stable rotation center (`cx`, `cy`) at creation. It's updated only by `move()`, not recomputed during `rotate()`. The O piece skips rotation entirely. This eliminates the accumulated translation that caused pieces to shift after a full 360° cycle.

2. **Touch blocked by overlay** — Added `pointer-events: none` to `#overlay` CSS so touch events pass through to the canvas, allowing mobile users to tap to start/restart.


## Key Decisions


## Changed Files


## Testing

<!-- -->
