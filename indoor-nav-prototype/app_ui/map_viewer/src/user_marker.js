/**
 * user_marker.js — User Position + Heading Direction Marker
 *
 * Draws a glowing cyan dot at the user's current tile with a direction arrow.
 */

const UserMarker = (() => {
  let _glow = 0;  // oscillating glow phase

  function draw(ctx, canvas, grid) {
    const u     = grid.user;
    const tileW = canvas.width  / grid.width;
    const tileH = canvas.height / grid.height;
    const cx    = (u.tx + 0.5) * tileW;
    const cy    = (u.ty + 0.5) * tileH;
    const r     = Math.max(tileW, tileH) * 0.55;

    _glow = (_glow + 0.06) % (Math.PI * 2);
    const glow = 0.5 + 0.5 * Math.sin(_glow);

    // Outer glow
    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r * 2.5);
    grad.addColorStop(0,   `rgba(96,239,255,${0.3 * glow})`);
    grad.addColorStop(1,   "rgba(96,239,255,0)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, r * 2.5, 0, Math.PI*2);
    ctx.fill();

    // Inner dot
    ctx.fillStyle = "#60efff";
    ctx.shadowColor = "#60efff";
    ctx.shadowBlur  = 8;
    ctx.beginPath();
    ctx.arc(cx, cy, r * 0.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;

    // Heading arrow
    const headRad = (u.heading_deg - 90) * Math.PI / 180;
    const arrowLen = r * 1.4;
    ctx.strokeStyle = "#60efff";
    ctx.lineWidth   = 2;
    ctx.lineCap     = "round";
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(headRad) * arrowLen,
               cy + Math.sin(headRad) * arrowLen);
    ctx.stroke();
  }

  return { draw };
})();
