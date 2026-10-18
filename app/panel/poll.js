(function () {
  var st = document.getElementById("st");
  function tick() {
    fetch("/auth/poll", {credentials: "same-origin"}).then(function (r) { return r.json(); }).then(function (d) {
      if (d.status === "ok") { location.href = "/"; return; }
      if (d.status === "denied") { st.className = "err"; st.textContent = "Rad etildi yoki muddati tugadi. Sahifani yangilang."; return; }
      setTimeout(tick, 2000);
    }).catch(function () { setTimeout(tick, 4000); });
  }
  tick();
})();
