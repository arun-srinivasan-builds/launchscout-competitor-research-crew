// LaunchScout "Back to top": one floating button for the whole app.
// Runs in the browser only: no network request, no Streamlit rerun, no session state access.
// Appearance comes from the .ls-top classes in ui/theme.py.
(function () {
  var ID = "ls-back-to-top";
  var THRESHOLD = 400;

  if (typeof window.__lsBackToTopCleanup === "function") {
    window.__lsBackToTopCleanup(); // a rerender replaces the previous listeners
  }

  function scroller() {
    return document.querySelector('[data-testid="stMain"]') || document.scrollingElement;
  }

  function position() {
    var el = scroller();
    return Math.max(el ? el.scrollTop : 0, window.pageYOffset || 0);
  }

  var button = document.getElementById(ID);
  if (!button) {
    button = document.createElement("button");
    button.id = ID;
    button.type = "button";
    button.className = "ls-top";
    button.setAttribute("aria-label", "Back to top");
    button.setAttribute("title", "Back to top");
    // The icon is built with DOM calls: Streamlit's sanitiser drops a script that contains
    // markup-looking strings, so no HTML string appears anywhere in this file.
    var NS = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("width", "20");
    svg.setAttribute("height", "20");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    var path = document.createElementNS(NS, "path");
    path.setAttribute("d", "M12 19V5M5 12l7-7 7 7");
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "currentColor");
    path.setAttribute("stroke-width", "2.4");
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    svg.appendChild(path);
    button.appendChild(svg);
    document.body.appendChild(button);
  }

  function update() {
    if (position() > THRESHOLD) {
      button.classList.add("ls-top-show");
    } else {
      button.classList.remove("ls-top-show");
    }
  }

  function toTop() {
    var reduce =
      window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var behavior = reduce ? "auto" : "smooth";
    var el = scroller();
    if (el && el.scrollTo) {
      el.scrollTo({ top: 0, behavior: behavior });
    }
    window.scrollTo({ top: 0, behavior: behavior });
  }

  // scroll events do not bubble; capture them from whichever element scrolls
  document.addEventListener("scroll", update, true);
  button.addEventListener("click", toTop);
  update();

  window.__lsBackToTopCleanup = function () {
    document.removeEventListener("scroll", update, true);
    button.removeEventListener("click", toTop);
  };
})();
