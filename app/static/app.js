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
            relevant: state.session.relevant,
            not_relevant: state.session.not_relevant,
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
    $("#relevant").value = (state.session.relevant || []).join("\n");
    $("#not-relevant").value = (state.session.not_relevant || []).join("\n");
    paintProve();
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
          relevant: lines($("#relevant").value),
          not_relevant: lines($("#not-relevant").value),
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
    card.innerHTML = `
      <span class="badge"></span>
      <p class="prompt"></p>
      <p class="verdict"></p>
      <ul class="rubric"></ul>
      <p class="why"></p>
      <p class="teach"></p>`;
    card.querySelector(".badge").textContent = row.badge;
    card.querySelector(".prompt").textContent = `“${row.prompt}”`;
    card.querySelector(".verdict").textContent = row.verdict;
    const list = card.querySelector(".rubric");
    if (row.rubric) {
      ["on_job", "complete", "safe", "cites_skill_steps"].forEach((key) => {
        const item = row.rubric[key];
        if (!item) return;
        const li = document.createElement("li");
        li.dataset.ok = item.passed ? "1" : "0";
        li.textContent = item.passed ? key : `${key} — ${item.why}`;
        list.appendChild(li);
      });
    }
    card.querySelector(".why").textContent = row.passed ? "" : row.why;
    card.querySelector(".teach").textContent = row.passed ? "" : row.teach;
    return card;
  }

  function paintProve() {
    const wakeBox = $("#wake-results");
    const outBox = $("#output-results");
    if (!wakeBox || !outBox) return;
    wakeBox.replaceChildren();
    outBox.replaceChildren();
    (state.session.benchmarks || []).forEach((row) => {
      const card = paintCard(row);
      (row.family === "output" ? outBox : wakeBox).appendChild(card);
    });
    const report = state.session.prove_report;
    const strip = $("#score-strip");
    const chipsBox = $("#score-chips");
    if (!report || !strip) return;
    strip.hidden = false;
    const recall = report.wake_recall || {};
    const precision = report.wake_precision || {};
    $("#score-num").textContent = `Recall ${recall.passed || 0}/${recall.total || 0} · Precision ${precision.passed || 0}/${precision.total || 0}`;
    chipsBox.replaceChildren();
    const rubric = report.output_rubric || {};
    ["on_job", "complete", "safe", "cites_skill_steps"].forEach((key) => {
      const vert = rubric[key];
      if (!vert) return;
      const chip = document.createElement("span");
      chip.className = "score-chip";
      chip.textContent = `${key} ${vert.passed}/${vert.total}`;
      chipsBox.appendChild(chip);
    });
    const composite = $("#composite-note");
    if (composite) {
      if (report.composite_0_100 == null) {
        composite.hidden = true;
      } else {
        composite.hidden = false;
        composite.textContent = `Optional composite ${report.composite_0_100}/100 — not acceptance.`;
      }
    }
    const note = $("#teach-note");
    if (note) {
      note.textContent = report.teachability_ok
        ? "Why on fail shown under the failing check."
        : "Teachability gate failed — every failure needs a why.";
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
