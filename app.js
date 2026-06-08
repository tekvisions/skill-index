/* The Skill Index — client. Fetch data.json, render the ledger, wire search/filter/sort. */
(function () {
  "use strict";
  var DATA = { items: [], categories: [], count: 0, generated_at: null };
  var state = { q: "", cat: "all", sort: "momentum" };

  var $ = function (s, r) { return (r || document).querySelector(s); };
  function esc(s) { return (s == null ? "" : String(s)).replace(/[&<>"']/g, function (m) {
    return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[m]; }); }
  function fmt(n) { return n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1) + "k" : String(n); }
  function ago(iso) {
    if (!iso) return "—";
    var d = (Date.now() - new Date(iso).getTime()) / 86400000;
    if (d < 1) return "today"; if (d < 2) return "1d ago";
    if (d < 30) return Math.round(d) + "d ago";
    if (d < 365) return Math.round(d / 30) + "mo ago";
    return Math.round(d / 365) + "y ago";
  }

  /* ── theme ── */
  var saved = null;
  try { saved = localStorage.getItem("si-theme"); } catch (e) {}
  if (saved) document.documentElement.setAttribute("data-theme", saved);
  $("#theme").addEventListener("click", function () {
    var cur = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", cur);
    try { localStorage.setItem("si-theme", cur); } catch (e) {}
  });

  function countUp(el, target) {
    var dur = 900, t0 = null;
    function step(t) {
      if (!t0) t0 = t;
      var p = Math.min((t - t0) / dur, 1), e = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(e * target);
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function matches(it) {
    if (state.cat !== "all" && it.category !== state.cat) return false;
    if (!state.q) return true;
    var q = state.q.toLowerCase();
    return (it.full_name + " " + it.description + " " + (it.topics || []).join(" ") + " " + it.category)
      .toLowerCase().indexOf(q) !== -1;
  }

  function sortItems(list) {
    var s = state.sort;
    return list.slice().sort(function (a, b) {
      if (s === "stars") return b.stars - a.stars;
      if (s === "new") return new Date(b.created_at || 0) - new Date(a.created_at || 0);
      return b.momentum - a.momentum || b.stars - a.stars;
    });
  }

  function card(it, i) {
    var foot = [];
    foot.push('<span>★ ' + fmt(it.stars) + "</span>");
    if (it.forks) foot.push("<span>⑂ " + fmt(it.forks) + "</span>");
    if (it.language) foot.push('<span class="lang">' + esc(it.language) + "</span>");
    foot.push("<span>" + ago(it.pushed_at) + "</span>");
    if (it.license) foot.push("<span>" + esc(it.license) + "</span>");
    return (
      '<a class="card" href="/p/' + esc(it.slug) + '/" style="transition-delay:' + (i % 12) * 35 + 'ms">' +
        '<span class="cat-tag">' + esc(it.category) + "</span>" +
        '<div class="card-top">' +
          '<div class="rank mono">' + String(it.rank).padStart(2, "0") + "</div>" +
          '<div class="card-id"><div class="name">' + esc(it.name) + "</div>" +
          '<div class="owner mono">' + esc(it.owner) + "</div></div>" +
        "</div>" +
        '<div class="desc">' + esc(it.description || "No description.") + "</div>" +
        '<div class="momentum"><div class="mbar"><i data-w="' + it.momentum + '"></i></div>' +
          '<div class="mscore mono">' + it.momentum + "</div></div>" +
        '<div class="card-foot mono">' + foot.join("") + "</div>" +
      "</a>"
    );
  }

  function render() {
    var list = sortItems(DATA.items.filter(matches));
    var grid = $("#grid");
    $("#metaline").textContent = list.length + (list.length === 1 ? " skill" : " skills") +
      (state.cat === "all" ? "" : " in " + state.cat) + (state.q ? ' matching "' + state.q + '"' : "");
    if (!list.length) { grid.innerHTML = '<div class="empty">No skills match. Try a broader search.</div>'; return; }
    grid.innerHTML = list.map(card).join("");
    var cards = grid.querySelectorAll(".card");
    requestAnimationFrame(function () {
      cards.forEach(function (c) { c.classList.add("in"); });
      grid.querySelectorAll(".mbar i").forEach(function (b) { b.style.width = b.getAttribute("data-w") + "%"; });
    });
  }

  function chips() {
    var box = $("#chips"), html = ['<button class="chip active" data-cat="all">All <span class="ct">' + DATA.count + "</span></button>"];
    DATA.categories.forEach(function (c) {
      html.push('<button class="chip" data-cat="' + esc(c.name) + '">' + esc(c.name) + ' <span class="ct">' + c.count + "</span></button>");
    });
    box.innerHTML = html.join("");
    box.addEventListener("click", function (e) {
      var b = e.target.closest(".chip"); if (!b) return;
      box.querySelectorAll(".chip").forEach(function (x) { x.classList.remove("active"); });
      b.classList.add("active"); state.cat = b.getAttribute("data-cat"); render();
    });
  }

  function boot() {
    $("#s-count").setAttribute("data-count", DATA.count);
    countUp($("#s-count"), DATA.count);
    countUp($("#s-cats"), DATA.categories.length);
    $("#s-top").textContent = DATA.items.length ? DATA.items[0].momentum : "—";
    if (DATA.generated_at) {
      var dt = new Date(DATA.generated_at);
      $("#edition").textContent = "— " + dt.toISOString().slice(0, 10) + " —";
      $("#foot-updated").textContent = "Last recomputed " + dt.toUTCString().replace("GMT", "UTC");
    }
    chips();
    render();
    var qi = $("#q"), t;
    qi.addEventListener("input", function () { clearTimeout(t); t = setTimeout(function () { state.q = qi.value.trim(); render(); }, 120); });
    $("#sort").addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return;
      $("#sort").querySelectorAll("button").forEach(function (x) { x.classList.remove("active"); });
      b.classList.add("active"); state.sort = b.getAttribute("data-sort"); render();
    });
  }

  fetch("/data.json?v=" + Date.now()).then(function (r) { return r.json(); }).then(function (d) {
    DATA = d; boot();
  }).catch(function () {
    $("#metaline").textContent = "Could not load the index. Refresh to retry.";
  });
})();
