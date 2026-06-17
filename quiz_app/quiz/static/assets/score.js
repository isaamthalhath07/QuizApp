// Shared scoring + full-screen feedback glow for every quiz round.
// Loaded once from base.html, so flashGlow() / recordScore() are global.
(function () {
  "use strict";

  // Full-viewport green/red glow that's visible no matter where you've scrolled.
  window.flashGlow = function (correct) {
    var el = document.getElementById("answer-glow");
    if (!el) {
      el = document.createElement("div");
      el.id = "answer-glow";
      document.body.appendChild(el);
    }
    el.classList.remove("show-correct", "show-wrong");
    // force reflow so the animation re-triggers on consecutive answers
    void el.offsetWidth;
    el.classList.add(correct ? "show-correct" : "show-wrong");
    clearTimeout(el._t);
    el._t = setTimeout(function () {
      el.classList.remove("show-correct", "show-wrong");
    }, 1400);
  };

  // Tiny "+10" chip that floats up near the answer area.
  function pointsPop(awarded) {
    if (!awarded) return;
    var pop = document.createElement("div");
    pop.className = "points-pop";
    pop.textContent = "+" + awarded;
    document.body.appendChild(pop);
    setTimeout(function () { pop.remove(); }, 1500);
  }

  // Keep any on-screen point counters in sync with the server total.
  function syncPoints(total) {
    var els = document.querySelectorAll("[data-points-total]");
    for (var i = 0; i < els.length; i++) els[i].textContent = total;
  }

  // POST one answer for authoritative re-grading + points. Fire-and-forget:
  // the glow has already fired locally, this just records the score.
  window.recordScore = function (payload) {
    try {
      fetch("/quiz/score/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": window.CSRF_TOKEN || ""
        },
        credentials: "same-origin",
        body: JSON.stringify(payload)
      })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (d) {
          if (!d) return;
          if (typeof d.points === "number") syncPoints(d.points);
          if (d.awarded) pointsPop(d.awarded);
        })
        .catch(function () {});
    } catch (e) {}
  };
})();
