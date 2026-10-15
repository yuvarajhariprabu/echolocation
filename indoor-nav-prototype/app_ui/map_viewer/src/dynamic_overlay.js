/**
 * dynamic_overlay.js — Dynamic Object Confidence Overlay
 *
 * Draws orange confidence "halos" over tiles with significant dynamic occupancy.
 * More opaque = higher confidence = closer/more certain moving object.
 */

const DynamicOverlay = (() => {

  function draw(ctx, canvas, grid) {
    const W     = grid.width;
    const H     = grid.height;
    const tileW = canvas.width  / W;
    const tileH = canvas.height / H;
    const dyn   = grid.dynamic;

    for (let ty = 0; ty < H; ty++) {
      for (let tx = 0; tx < W; tx++) {
        const conf = dyn[ty][tx];
        if (conf < 0.1) continue;

        const cx = (tx + 0.5) * tileW;
        const cy = (ty + 0.5) * tileH;
        const r  = Math.max(tileW, tileH) * 0.7;

        const alpha = Math.min(conf * 0.8, 0.8);
        const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
        grad.addColorStop(0,   `rgba(249,115,22,${alpha})`);
        grad.addColorStop(0.6, `rgba(249,115,22,${alpha * 0.4})`);
        grad.addColorStop(1,   "rgba(249,115,22,0)");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  return { draw };
})();
