/* ==========================================================================
   Digital rain — sparse green 0/1 columns falling behind the dashboard.

   Performance notes:
   - one canvas, one rAF loop throttled to ~24fps (the eye cannot tell);
   - no layout reads inside the loop; the transform is set once per resize;
   - the trail is produced with destination-out, so the page background stays
     transparent behind the glyphs instead of being painted over;
   - stops on hidden tabs and on prefers-reduced-motion (draws one static
     field instead of animating).
   ========================================================================== */
(function () {
  "use strict";

  var canvas = document.getElementById("rain");
  if (!canvas) return;

  var ctx = canvas.getContext("2d", { alpha: true });
  if (!ctx) return; // jsdom and other headless DOMs have no 2D context

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  var FONT = 15;
  var FPS = 24;
  var INTERVAL = 1000 / FPS;

  var width = 0;
  var height = 0;
  var columns = 0;
  var drops = [];
  var speeds = [];
  var last = 0;
  var raf = 0;

  function resize() {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    columns = Math.max(1, Math.floor(width / FONT));
    drops = new Array(columns);
    speeds = new Array(columns);
    for (var i = 0; i < columns; i += 1) {
      drops[i] = Math.random() * -40;          // staggered start above the fold
      speeds[i] = 0.45 + Math.random() * 0.85; // rows per frame
    }
  }

  function drawColumn(index) {
    var x = index * FONT + 3;
    var y = drops[index] * FONT;
    if (y < -FONT) return;

    // "Head" glyph is brighter than the trail behind it.
    ctx.fillStyle = "rgba(134, 239, 172, 0.55)";
    ctx.fillText(Math.random() > 0.5 ? "1" : "0", x, y);
  }

  function frame(now) {
    raf = requestAnimationFrame(frame);
    if (now - last < INTERVAL) return;
    last = now;

    // Fade what is already there instead of painting the page background.
    ctx.globalCompositeOperation = "destination-out";
    ctx.fillStyle = "rgba(0, 0, 0, 0.055)";
    ctx.fillRect(0, 0, width, height);
    ctx.globalCompositeOperation = "source-over";

    ctx.font = FONT + 'px "JetBrains Mono", ui-monospace, monospace';
    ctx.textBaseline = "top";

    for (var i = 0; i < columns; i += 1) {
      drawColumn(i);
      drops[i] += speeds[i];
      if (drops[i] * FONT > height && Math.random() > 0.972) {
        drops[i] = Math.random() * -12;
        speeds[i] = 0.45 + Math.random() * 0.85;
      }
    }
  }

  function start() {
    if (raf) return;
    last = 0;
    raf = requestAnimationFrame(frame);
  }

  function stop() {
    if (!raf) return;
    cancelAnimationFrame(raf);
    raf = 0;
  }

  function drawStill() {
    // Reduced motion: a single static field, no animation.
    ctx.clearRect(0, 0, width, height);
    ctx.font = FONT + 'px "JetBrains Mono", ui-monospace, monospace';
    ctx.textBaseline = "top";
    for (var i = 0; i < columns; i += 1) {
      var rows = Math.floor(Math.random() * 14) + 2;
      for (var row = 0; row < rows; row += 1) {
        var y = (drops[i] + row) * FONT;
        if (y > height) break;
        ctx.fillStyle = "rgba(134, 239, 172, " + (0.16 - row * 0.01) + ")";
        ctx.fillText(Math.random() > 0.5 ? "1" : "0", i * FONT + 3, y);
      }
    }
  }

  function applyPreference() {
    stop();
    if (reduce.matches) {
      drawStill();
    } else if (!document.hidden) {
      start();
    }
  }

  var resizeTimer = 0;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      resize();
      if (reduce.matches) drawStill();
    }, 180);
  });

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) stop();
    else applyPreference();
  });

  if (reduce.addEventListener) reduce.addEventListener("change", applyPreference);

  resize();
  applyPreference();
})();
