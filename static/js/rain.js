/* ==========================================================================
   Digital rain, CSS-only.

   Each column is two identical halves; its height is 2x the viewport, so a
   translateY from -50% to 0 lands on the same pixels and the loop has no seam.
   Only transform animates, which the compositor can run off the main thread.

   prefers-reduced-motion freezes the columns (a readable static field).
   Append ?rain=on to force the animation for a demo on such a machine.
   ========================================================================== */
(function () {
  "use strict";

  var host = document.getElementById("rain");
  if (!host) return;

  if (/[?&]rain=on(?:&|$)/.test(window.location.search)) {
    document.body.dataset.rain = "on";
  }

  var rebuildTimer = 0;

  function digits(count) {
    var out = "";
    for (var i = 0; i < count; i += 1) {
      out += Math.random() > 0.5 ? "1" : "0";
      if (i < count - 1) out += "\n";
    }
    return out;
  }

  function build() {
    var width = window.innerWidth;
    var height = window.innerHeight;
    var fontSize = width < 640 ? 13 : 15;
    var lineHeight = fontSize * 1.18;

    // One half must cover the viewport, otherwise a gap appears at the bottom
    // of the loop.
    var lines = Math.ceil(height / lineHeight) + 2;
    var gap = width < 640 ? 44 : 32;
    var columns = Math.max(8, Math.min(48, Math.floor(width / gap)));

    host.textContent = "";
    var fragment = document.createDocumentFragment();

    for (var i = 0; i < columns; i += 1) {
      var column = document.createElement("span");
      column.className = "rain-col";
      column.setAttribute("aria-hidden", "true");

      var half = digits(lines);
      column.textContent = half + "\n" + half;   // identical halves

      column.style.left = (((i + 0.5) * 100) / columns).toFixed(2) + "%";
      column.style.fontSize = fontSize + "px";
      column.style.setProperty("--rain-speed", (12 + Math.random() * 12).toFixed(1) + "s");
      column.style.animationDelay = (-Math.random() * 24).toFixed(1) + "s";
      column.style.opacity = (0.3 + Math.random() * 0.45).toFixed(2);

      fragment.appendChild(column);
    }

    host.appendChild(fragment);
  }

  window.addEventListener("resize", function () {
    clearTimeout(rebuildTimer);
    rebuildTimer = setTimeout(build, 220);
  });

  build();
})();
