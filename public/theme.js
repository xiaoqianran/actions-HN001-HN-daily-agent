
(function () {
  var root = document.documentElement;
  var btn = document.getElementById("theme-toggle");
  if (!btn) return;

  function labelFor(theme) {
    return theme === "latte" ? "Latte" : "Mocha";
  }

  function apply(theme) {
    root.setAttribute("data-theme", theme);
    try { localStorage.setItem("ctp-theme", theme); } catch (e) {}
    var label = btn.querySelector(".theme-label");
    if (label) label.textContent = labelFor(theme);
    btn.setAttribute("aria-label", "当前主题 " + labelFor(theme) + "，点击切换");
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "latte" ? "#eff1f5" : "#1e1e2e");
  }

  var current = root.getAttribute("data-theme") || "mocha";
  apply(current);

  btn.addEventListener("click", function () {
    var next = (root.getAttribute("data-theme") === "latte") ? "mocha" : "latte";
    apply(next);
  });
})();
