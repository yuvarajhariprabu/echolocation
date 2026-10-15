/**
 * path_overlay.js — A* Path Visualization
 *
 * Draws the current planned path as a glowing purple line through tile centres.
 * Animates a "scout" dot moving along the path.
 */

const PathOverlay = (() => {
  let _progress = 0;

  function draw(ctx, canvas, grid, path) {
    if (!path || path.length < 2) return;

    const tileW = canvas.width  / grid.width;
    const tileH = canvas.height / grid.height;

    const pts = path.map(([tx, ty]) => ({
      x: (tx + 0.5) * tileW,
      y: (ty + 0.5) * tileH,
    }));

    // Glow shadow
    ctx.shadowColor = "#a78bfa";
    ctx.shadowBlur  = 6;

    // Path line
    ctx.strokeStyle = "rgba(167,139,250,0.6)";
    ctx.lineWidth   = 2;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
    ctx.stroke();
    ctx.setLineDash([]);

    // Goal marker
    const g = pts[pts.length - 1];
    ctx.fillStyle   = "#a78bfa";
    ctx.shadowBlur  = 12;
    ctx.beginPath();
    ctx.arc(g.x, g.y, 5, 0, Math.PI * 2);
    ctx.fill();

    // Animated scout dot
    _progress = (_progress + 0.01) % 1.0;
    const segment = Math.floor(_progress * (pts.length - 1));
    const frac    = (_progress * (pts.length - 1)) - segment;
    const a       = pts[segment];
    const b       = pts[Math.min(segment+1, pts.length-1)];
    const sx = a.x + (b.x - a.x) * frac;
    const sy = a.y + (b.y - a.y) * frac;

    ctx.fillStyle  = "rgba(167,139,250,0.9)";
    ctx.shadowBlur = 8;
    ctx.beginPath();
    ctx.arc(sx, sy, 3, 0, Math.PI*2);
    ctx.fill();

    ctx.shadowBlur = 0;
  }

  return { draw };
})();
