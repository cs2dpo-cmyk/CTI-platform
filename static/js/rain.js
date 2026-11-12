/* ==========================================================================
   Digital rain: short 0/1 streams at random positions, falling at random
   speeds. Every stream is a separate composited layer animating transform only.

   The effect is decorative and the product owner asked for it to run even when
   the OS reports prefers-reduced-motion, so this layer always animates; the
   rest of the dashboard still honours the preference.
   ========================================================================== */
(function () {
  "use strict";

  var host = document.getElementById("rain");
  if (!host) return;

  var rebuildTimer = 0;

  function digits(length) {
    var out = "";
    for (var i = 0; i < length; i += 1) {
      out += Math.random() > 0.5 ? "1" : "0";
      if (i < length - 1) out += "\n";
    }
    return out;
  }

  function build() {
    var width = window.innerWidth;
    var gap = width < 640 ? 30 : 24;
    var count = Math.max(10, Math.min(64, Math.round(width / gap)));

    host.textContent = "";
    var fragment = document.createDocumentFragment();

    for (var i = 0; i < count; i += 1) {
      var stream = document.createElement("span");
      stream.className = "rain-stream";
      stream.setAttribute("aria-hidden", "true");

      var length = 7 + Math.floor(Math.random() * 16);   // 7–22 glyphs
      stream.textContent = digits(length);

      stream.style.left = (Math.random() * 100).toFixed(2) + "%";
      stream.style.fontSize = (width < 640 ? 13 : 15) + "px";
      stream.style.setProperty("--rain-speed", (3.6 + Math.random() * 5.4).toFixed(1) + "s");
      stream.style.animationDelay = (-Math.random() * 9).toFixed(1) + "s";
      stream.style.opacity = (0.35 + Math.random() * 0.55).toFixed(2);

      fragment.appendChild(stream);
    }

    host.appendChild(fragment);
  }

  window.addEventListener("resize", function () {
    clearTimeout(rebuildTimer);
    rebuildTimer = setTimeout(build, 220);
  });

  build();
})();
