(() => {
  const FLOW = [
    { id: "start", t: "Start" },
    { id: "describe", t: "Describe" },
    { id: "build", t: "Build" },
    { id: "prove", t: "Prove" },
    { id: "dispose", t: "Keep/Throw" },
    { id: "done", t: "Done" },
  ];

  const NAV = {
    start: "01 · Start",
    describe: "02 · Describe",
    build: "03 · Build",
    prove: "04 · Prove",
    dispose: "05 · Keep / Throw",
    done_keep: "06 · Done",
    done_throw: "06 · Done",
  };

  const state = {
    session: null,
    jobDraft: "",
    screen: "start",
    hold: null,
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const app = $("#app");
  const navStep = $("#nav-step");
  const chips = $("#chips");

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { "content-type": "application/json", ...(opts.headers || {}) },
      ...opts,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = data?.detail?.message || data?.detail || res.statusText;
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    return data;
  }

  function mount(id) {
    const tpl = document.getElementById(id);
    app.replaceChildren(tpl.content.cloneNode(true));
  }

  function lines(value) {
    return (value || "")
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
  }

  function currentChip() {
    if (state.hold === "describe") return "describe";
    const step = state.session?.step || state.screen;
    if (step === "done_keep" || step === "done_throw") return "done";
    if (step === "job" || !state.session) return "start";
    return step;
  }

  function paintChips() {
    const current = currentChip();
    chips.replaceChildren();
    FLOW.forEach((item, i) => {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.dataset.on = item.id === current ? "1" : "0";
      btn.textContent = item.t;
      li.appendChild(btn);
      if (i < FLOW.length - 1) {
        const arrow = document.createElement("span");
        arrow.className = "arrow";
        arrow.textContent = "→";
        li.appendChild(arrow);
      }
      chips.appendChild(li);
    });
  }

  function render() {
    const step = state.hold || state.session?.step || state.screen || "start";
    navStep.textContent = NAV[step] || NAV.start;
    paintChips();
    if (state.hold === "describe" || step === "describe") return renderDescribe();
    if (!state.session || step === "start" || step === "job") return renderStart();
    if (step === "build") return renderBuild();
    if (step === "prove") return renderProve();
    if (step === "dispose") return renderDispose();
    if (step === "done_keep" || step === "done_throw") return renderDone();
    return renderStart();
  }

  function renderStart() {
    state.screen = "start";
    state.hold = null;
    navStep.textContent = NAV.start;
    paintChips();
    mount("tpl-start");
    const input = $("#job");
    input.value = state.jobDraft || state.session?.job || "";
    const go = async (e) => {
      const job = input.value.trim();
      if (!job) {
        input.focus();
        return;
      }
      state.jobDraft = job;
      e.currentTarget.disabled = true;
      try {
        state.session = await api("/api/sessions", {
          method: "POST",
          body: JSON.stringify({ job }),
        });
        state.hold = "describe";
        render();
      } catch (err) {
        alert(err.message);
        e.currentTarget.disabled = false;
      }
    };
    $("#start-continue").addEventListener("click", go);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        $("#start-continue").click();
      }
    });
  }

  function renderDescribe() {
    mount("tpl-describe");
    const job = state.session?.job || state.jobDraft || "";
    $("#describe-job").textContent = job;
    $("#describe-name").textContent = state.session?.name || "—";
    $("#describe-wake").textContent = state.session?.when || job;
    $("#describe-continue").addEventListener("click", () => {
      state.hold = null;
      render();
    });
  }

  function renderBuild() {
    mount("tpl-build");
    $("#method").value = state.session.method || "description";
    $("#when").value = state.session.when || "";
    $("#not-when").value = state.session.not_when || "";
    $("#body").value = state.session.body || "";
    $("#depth-nested").checked = !!state.session.depth?.nested;
    $("#depth-tools").checked = !!state.session.depth?.tools;
    $("#depth-scripts").checked = !!state.session.depth?.scripts;
    if (state.session.depth?.nested || state.session.depth?.tools || state.session.depth?.scripts) {
      $("#depth-panel").open = true;
    }
    $("#build-continue").addEventListener("click", async (e) => {
      e.currentTarget.disabled = true;
      try {
        state.session = await api(`/api/sessions/${state.session.id}/build`, {
          method: "POST",
          body: JSON.stringify({
            when: $("#when").value,
            not_when: $("#not-when").value,
            body: $("#body").value,
            method: $("#method").value,
            should: state.session.should,
            should_not: state.session.should_not,
            near_miss: state.session.near_miss,
            with_skill: state.session.with_skill || state.session.relevant,
            without_skill: state.session.without_skill || state.session.not_relevant,
            depth: {
              nested: !!$("#depth-nested")?.checked,
              tools: !!$("#depth-tools")?.checked,
              scripts: !!$("#depth-scripts")?.checked,
            },
            continue_to_prove: true,
          }),
        });
        render();
      } catch (err) {
        alert(err.message);
        e.currentTarget.disabled = false;
      }
    });
  }

  function renderProve() {
    mount("tpl-prove");
    $("#should").value = (state.session.should || []).join("\n");
    $("#should-not").value = (state.session.should_not || []).join("\n");
    $("#near-miss").value = (state.session.near_miss || []).join("\n");
    $("#with-skill").value = (state.session.with_skill || state.session.relevant || []).join("\n");
    $("#without-skill").value = (state.session.without_skill || state.session.not_relevant || []).join("\n");
    paintProve();
    if (!state.session.proved) {
      const wakeEdit = $("#wake-edit");
      const outEdit = $("#output-edit");
      if (wakeEdit) wakeEdit.open = true;
      if (outEdit) outEdit.open = true;
    }
    $("#prove-continue").disabled = !state.session.proved;
    $("#run-check").addEventListener("click", () => runProve(false));
    $("#prove-continue").addEventListener("click", () => runProve(true));
  }

  async function runProve(continueToDispose) {
    const err = $("#prove-error");
    if (err) err.hidden = true;
    try {
      state.session = await api(`/api/sessions/${state.session.id}/prove`, {
        method: "POST",
        body: JSON.stringify({
          when: state.session.when,
          not_when: state.session.not_when,
          should: lines($("#should").value),
          should_not: lines($("#should-not").value),
          near_miss: lines($("#near-miss").value),
          with_skill: lines($("#with-skill").value),
          without_skill: lines($("#without-skill").value),
          continue_to_dispose: continueToDispose,
        }),
      });
      if (continueToDispose) return render();
      paintProve();
      $("#prove-continue").disabled = !state.session.proved;
    } catch (e) {
      if (err) {
        err.hidden = false;
        err.textContent = e.message;
      } else {
        alert(e.message);
      }
    }
  }

  function paintCard(row) {
    const card = document.createElement("article");
    card.className = "case-card";
    const ev = row.evidence || {};
    const fixture = ev.fixture || row.prompt || row.sample || "";
    card.innerHTML = `
      <span class="badge"></span>
      <p class="prompt"></p>
      <p class="verdict"></p>
      <p class="evidence"></p>
      <p class="why"></p>`;
    card.querySelector(".badge").textContent = row.badge || row.kind || "";
    card.querySelector(".prompt").textContent = `“${fixture}”`;
    card.querySelector(".verdict").textContent = row.verdict || "";
    const bits = [];
    if (ev.hits && ev.hits.length) bits.push(ev.hits.slice(0, 6).join(", "));
    if (row.trigger_rate != null) bits.push(`rate ${row.trigger_rate}`);
    if (row.judge) bits.push(row.judge);
    card.querySelector(".evidence").textContent = bits.join(" · ");
    card.querySelector(".why").textContent = row.why || "";
    return card;
  }

  function paintProve() {
    const wakeBox = $("#wake-results");
    const outBox = $("#output-results");
    if (!wakeBox || !outBox) return;
    wakeBox.replaceChildren();
    outBox.replaceChildren();
    const report = state.session.prove_report || {};
    const wakeCases = report.wake?.cases || (state.session.benchmarks || []).filter((r) => r.family === "wake");
    const outCases = report.output?.cases || (state.session.benchmarks || []).filter((r) => r.family === "output");
    wakeCases.forEach((row) => wakeBox.appendChild(paintCard(row)));
    outCases.forEach((row) => outBox.appendChild(paintCard(row)));
    const meta = $("#prove-meta");
    if (meta && report.wake) {
      const r = report.wake.recall;
      const p = report.wake.precision;
      const honest = report.wake.harness_honesty ? "honest" : "inconsistent";
      meta.textContent = `Wake P/R (observation only): recall ${r ?? "—"} · precision ${p ?? "—"} · harness ${honest}. Human Keep / Throw — no numeric floor.`;
    }
  }

  function renderDispose() {
    mount("tpl-dispose");
    const err = $("#dispose-error");
    $("#keep").addEventListener("click", async () => {
      try {
        state.session = await api(`/api/sessions/${state.session.id}/keep`, { method: "POST" });
        render();
      } catch (e) {
        err.hidden = false;
        err.textContent = e.message;
      }
    });
    $("#throw").addEventListener("click", async () => {
      try {
        state.session = await api(`/api/sessions/${state.session.id}/throw`, { method: "POST" });
        render();
      } catch (e) {
        err.hidden = false;
        err.textContent = e.message;
      }
    });
  }

  function renderDone() {
    mount("tpl-done");
    const kept = state.session.disposed === "keep";
    $("#keep-outcome").dataset.on = kept ? "1" : "0";
    $("#throw-outcome").dataset.on = kept ? "0" : "1";
    if (kept) {
      $("#keep-path").textContent = state.session.written_path || `${state.session.name}/SKILL.md`;
      const tree = (state.session.pack_tree || []).join("\n");
      $("#keep-tree").textContent = tree;
      $("#open-skill").hidden = false;
      $("#open-skill").addEventListener("click", () => {
        window.open(`/api/sessions/${state.session.id}/skill`, "_blank");
      });
    } else {
      $("#keep-path").textContent = "Not written.";
      $("#keep-tree").textContent = "";
    }
    $("#done-again").addEventListener("click", reset);
  }

  function reset() {
    state.session = null;
    state.jobDraft = "";
    state.hold = null;
    state.screen = "start";
    renderStart();
  }

  render();
})();
