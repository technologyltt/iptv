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
    $("maf").textContent = fmt(s.maf_gs, 1);
    $("ect").textContent = fmt(s.coolant_c, 0);
    $("iat").textContent = fmt(s.intake_c, 0);
    $("pedal").textContent = fmt(s.pedal_pct, 0);
    $("thr").textContent = fmt(s.throttle_pct, 0);

    // DTCs
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

    // Auto-clear toggle (no pisar al usuario)
    const auto = $("auto-clear");
    if (document.activeElement !== auto) auto.checked = !!s.auto_clear;

    // Modo sonido
    if (s.sound) {
      for (const btn of document.querySelectorAll(".mode")) {
        btn.classList.toggle("active", btn.dataset.mode === s.sound.mode);
      }
      const badge = $("sound-open");
      badge.textContent = s.sound.open ? "ABIERTA" : "CERRADA";
      badge.classList.toggle("on", !!s.sound.open);
      $("sound-reason").textContent = s.sound.reason || "—";
    }

    // Relés
    if (s.relays) {
      for (const r of s.relays) {
        const btn = document.querySelector(`.relay[data-id="${r.id}"]`);
        if (!btn) continue;
        btn.classList.toggle("on", !!r.state);
        btn.querySelector(".rstate").textContent = r.state ? "ON" : "OFF";
      }
    }
  });

  // Borrar manual
  $("btn-clear").addEventListener("click", async () => {
    const btn = $("btn-clear");
    btn.disabled = true;
    btn.textContent = "Borrando…";
    try {
      const r = await fetch("/api/clear", { method: "POST" }).then(r => r.json());
      if (r.ok) {
        btn.textContent = r.cleared && r.cleared.length
          ? `Borrados: ${r.cleared.join(", ")}`
          : "Nada que borrar";
      } else {
        btn.textContent = `Bloqueado: ${r.reason}`;
      }
    } catch (e) {
      btn.textContent = "Error de red";
    }
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = "Borrar fallos ahora";
    }, 2000);
  });

  $("auto-clear").addEventListener("change", async (e) => {
    await fetch("/api/auto_clear", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ enabled: e.target.checked }),
    });
  });

  // Modo sonido
  for (const btn of document.querySelectorAll(".mode")) {
    btn.addEventListener("click", async () => {
      const mode = btn.dataset.mode;
      await fetch("/api/sound/mode", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ mode }),
      });
    });
  }

  // Relés
  for (const btn of document.querySelectorAll(".relay")) {
    btn.addEventListener("click", async () => {
      const id = Number(btn.dataset.id);
      await fetch(`/api/relay/${id}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: "{}",
      });
    });
  }
})();
