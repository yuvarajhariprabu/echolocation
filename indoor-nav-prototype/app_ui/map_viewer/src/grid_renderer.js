/**
 * grid_renderer.js — Static + Dynamic Tile Grid Renderer
 *
 * Draws the tile grid onto the canvas using ImageData for performance.
 * Colors:
 *   Static occupied  → #ef4444 (red)
 *   Dynamic (hot)    → #f97316 interpolated by confidence
 *   Free             → #0a1020 (near-black)
 */

const GridRenderer = (() => {

  const COLORS = {
    free:    [10, 16, 32],       // dark blue-black
    static:  [239, 68, 68],      // red
    dynBase: [249, 115, 22],     // orange
    unknown: [20, 35, 60],       // unexplored blue-grey
  };

  function lerpColor(a, b, t) {
    return [
      Math.round(a[0] + (b[0]-a[0]) * t),
      Math.round(a[1] + (b[1]-a[1]) * t),
      Math.round(a[2] + (b[2]-a[2]) * t),
    ];
  }

  function draw(ctx, canvas, grid) {
    const W         = grid.width;
    const H         = grid.height;
    const tileW     = canvas.width  / W;
    const tileH     = canvas.height / H;
    const imgData   = ctx.createImageData(canvas.width, canvas.height);
    const buf       = imgData.data;
    const staticArr = grid.static;
    const dynArr    = grid.dynamic;

    for (let ty = 0; ty < H; ty++) {
      for (let tx = 0; tx < W; tx++) {
        const staticVal = staticArr[ty][tx];
        const dynConf   = dynArr[ty][tx];

        let color;
        if (staticVal === 1) {
          color = COLORS.static;
        } else if (dynConf > 0.05) {
          // interpolate free → dynBase by confidence
          color = lerpColor(COLORS.free, COLORS.dynBase, Math.min(dynConf, 1.0));
        } else if (staticVal === -1) {
          color = COLORS.unknown;
        } else {
          color = COLORS.free;
        }

        // Fill tile pixels
        const px0 = Math.floor(tx * tileW);
        const py0 = Math.floor(ty * tileH);
        const px1 = Math.floor((tx+1) * tileW);
        const py1 = Math.floor((ty+1) * tileH);

        for (let py = py0; py < py1; py++) {
          for (let px = px0; px < px1; px++) {
            const i = (py * canvas.width + px) * 4;
            buf[i]   = color[0];
            buf[i+1] = color[1];
            buf[i+2] = color[2];
            buf[i+3] = 255;
          }
        }
      }
    }

    ctx.putImageData(imgData, 0, 0);

    // Draw subtle grid lines (only when zoomed in / large tiles)
    if (tileW > 6) {
      ctx.strokeStyle = "rgba(30,48,80,0.3)";
      ctx.lineWidth = 0.5;
      for (let tx = 0; tx <= W; tx++) {
        ctx.beginPath();
        ctx.moveTo(tx * tileW, 0);
        ctx.lineTo(tx * tileW, canvas.height);
        ctx.stroke();
      }
      for (let ty = 0; ty <= H; ty++) {
        ctx.beginPath();
        ctx.moveTo(0, ty * tileH);
        ctx.lineTo(canvas.width, ty * tileH);
        ctx.stroke();
      }
    }
  }

  return { draw };
})();
