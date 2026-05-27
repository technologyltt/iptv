(() => {
  const $ = (id) => document.getElementById(id);
  const fmt = (v, d = 0) => (v == null ? "—" : Number(v).toFixed(d));

  const socket = io({ transports: ["websocket", "polling"] });

  socket.on("connect", () => {
    $("conn").textContent = "conectado";
    $("conn").classList.remove("off"); $("conn").classList.add("on");
  });
  socket.on("disconnect", () => {
    $("conn").textContent = "desconectado";
    $("conn").classList.add("off"); $("conn").classList.remove("on");
  });

  socket.on("status", (s) => {
    $("rpm").textContent = fmt(s.rpm, 0);
    $("speed").textContent = fmt(s.speed_kmh, 0);
    $("boost").textContent = fmt(s.boost_bar, 2);
    $("ect").textContent = fmt(s.coolant_c, 0);
    $("maf").textContent = fmt(s.maf_gs, 1);
    $("pedal").textContent = fmt(s.pedal_pct, 0);

    const ul = $("dtcs");
    ul.innerHTML = "";
    if (!s.dtcs || s.dtcs.length === 0) {
      ul.innerHTML = '<li class="empty">sin fallos</li>';
    } else {
      for (const [code, desc] of s.dtcs) {
        const li = document.createElement("li");
        li.innerHTML = `<span class="code">${code}</span><span class="desc">${desc || ""}</span>`;
        ul.appendChild(li);
      }
    }

    if (s.turbo) {
      const el = $("vtg-state");
      el.textContent = s.turbo.state.toUpperCase();
      el.classList.toggle("engaged", s.turbo.state === "engaged");
      el.classList.toggle("bypass", s.turbo.state === "bypass");
      $("last-action").textContent = s.turbo.last_action || "—";
      const busy = !!s.turbo.busy;
      $("btn-bypass").disabled = busy || s.turbo.state === "bypass";
      $("btn-engage").disabled = busy || s.turbo.state === "engaged";
    }
  });

  async function callTurbo(action, btn, label) {
    btn.disabled = true;
    const orig = btn.textContent;
    btn.textContent = "Procesando…";
    try {
      const r = await fetch(`/api/turbo/${action}`, { method: "POST" }).then(r => r.json());
      if (!r.ok) {
        btn.textContent = `Bloqueado: ${r.reason}`;
        setTimeout(() => { btn.textContent = orig; btn.disabled = false; }, 2500);
      } else {
        btn.textContent = orig;
      }
    } catch (e) {
      btn.textContent = "Error red";
      setTimeout(() => { btn.textContent = orig; btn.disabled = false; }, 2500);
    }
  }

  $("btn-bypass").addEventListener("click", (e) => callTurbo("bypass", e.currentTarget));
  $("btn-engage").addEventListener("click", (e) => callTurbo("engage", e.currentTarget));

  $("btn-clear").addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    btn.textContent = "Borrando…";
    try {
      const r = await fetch("/api/clear", { method: "POST" }).then(r => r.json());
      btn.textContent = r.ok ? "Borrados" : `Bloqueado: ${r.reason}`;
    } catch {
      btn.textContent = "Error red";
    }
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = "Borrar todos los fallos";
    }, 2000);
  });
})();
