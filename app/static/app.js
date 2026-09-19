(() => {
  const FLOW = [
    { id: "start", n: "1", t: "Start", d: "Empty state — make a skill that knows when to help" },
    { id: "job", n: "2", t: "Describe", d: "Say the job in plain words" },
    { id: "build", n: "3", t: "Build", d: "Steer method, body, nested pieces" },
    { id: "prove", n: "4", t: "Prove", d: "Should wake / should not — with why" },
    { id: "dispose", n: "5", t: "Keep / Throw", d: "Sacred dispose gate" },
    { id: "done", n: "6", t: "Done", d: "Path to pack — or nothing saved" },
  ];

  const NAV = {
    start: "1 · Start",
    job: "2 · Describe",
    build: "3 · Build",
    prove: "4 · Prove",
    dispose: "5 · Keep / Throw",
    done_keep: "6 · Done",
    done_throw: "6 · Done",
  };

  const state = {
    session: null,
    methods: null,
    picked: "description",
    screen: "start",
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const app = $("#app");
  const navStep = $("#nav-step");
  const rail = $("#rail");

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

  function paintRail() {
    const step = state.session?.step || state.screen;
    const current =
      step === "done_keep" || step === "done_throw" ? "done" : step === "start" || !state.session ? "start" : step;
    rail.replaceChildren();
    FLOW.forEach((item) => {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.dataset.on = item.id === current ? "1" : "0";
      btn.innerHTML = `<span class="n">${item.n}</span><span class="t">${item.t}</span><span class="d">${item.d}</span>`;
      li.appendChild(btn);
      rail.appendChild(li);
    });
  }

  function paintPack(el, session) {
    if (!el || !session) return;
    const tree = (session.pack_tree || []).join("\n");
    el.innerHTML = `<p class="kicker"></p><h2></h2><pre></pre>`;
    el.querySelector(".kicker").textContent =
      session.disposed === "keep" ? "SKILL PACK  ·  AFTER KEEP" : "SKILL PACK  ·  ONLY AFTER KEEP";
    el.querySelector("h2").textContent = `${session.name}/`;
    el.querySelector("pre").textContent = tree.split("\n").slice(1).join("\n");
  }

  function render() {
    const step = state.session?.step || state.screen || "start";
    navStep.textContent = NAV[step] || NAV.start;
    paintRail();
    if (!state.session || step === "job") return renderJob();
    if (step === "build") return renderBuild();
    if (step === "prove") return renderProve();
    if (step === "dispose") return renderDispose();
    if (step === "done_keep") return renderDoneKeep();
    if (step === "done_throw") return renderDoneThrow();
    return renderStart();
  }

  function renderStart() {
    state.screen = "start";
    navStep.textContent = NAV.start;
    paintRail();
    mount("tpl-start");
    const grid = $("#start-flow");
    FLOW.forEach((item) => {
      const card = document.createElement("article");
      card.className = "flow-card";
      card.innerHTML = `<span class="n">${item.n}</span><strong>${item.t}</strong><span>${item.d}</span>`;
      grid.appendChild(card);
    });
    $("#start-workshop").addEventListener("click", () => {
      state.screen = "job";
      renderJob();
    });
  }

  function renderJob() {
    mount("tpl-job");
    const ta = $("#job");
    if (state.session?.job) ta.value = state.session.job;
    $("#job-continue").addEventListener("click", async (e) => {
      const job = ta.value.trim();
      if (!job) {
        ta.focus();
        return;
      }
      e.currentTarget.disabled = true;
      try {
        state.session = await api("/api/sessions", {
          method: "POST",
          body: JSON.stringify({ job }),
        });
        state.picked = state.session.method || "description";
        render();
      } catch (err) {
        alert(err.message);
        e.currentTarget.disabled = false;
      }
    });
  }

  function renderBuild() {
    mount("tpl-build");
    const cite = state.methods?.citation;
    if (cite) {
      const a = $("#academy-cite");
      a.href = cite.url;
      a.textContent = cite.label;
    }
    state.picked = state.session.method || state.picked || "description";
    const cards = $("#method-cards");
    (state.methods?.methods || []).forEach((m) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "card" + (state.picked === m.id ? " sel" : "");
      btn.innerHTML = `<strong>${m.name}</strong><span>${m.card}</span>`;
      btn.addEventListener("click", () => {
        state.picked = m.id;
        renderBuild();
      });
      cards.appendChild(btn);
    });
    $("#when").value = state.session.when || "";
    $("#not-when").value = state.session.not_when || "";
    $("#body").value = state.session.body || "";
    $("#depth-nested").checked = !!state.session.depth?.nested;
    $("#depth-tools").checked = !!state.session.depth?.tools;
    $("#depth-scripts").checked = !!state.session.depth?.scripts;
    if (state.session.depth?.nested || state.session.depth?.tools || state.session.depth?.scripts) {
      $("#depth-panel").open = true;
    }
    paintPack($("#build-pack"), state.session);
    $("#build-continue").addEventListener("click", async (e) => {
      e.currentTarget.disabled = true;
      try {
        state.session = await api(`/api/sessions/${state.session.id}/build`, {
          method: "POST",
          body: JSON.stringify(buildPayload(true)),
        });
        render();
      } catch (err) {
        alert(err.message);
        e.currentTarget.disabled = false;
      }
    });
  }

  function buildPayload(continueToProve) {
    return {
      when: $("#when").value,
      not_when: $("#not-when").value,
      body: $("#body") ? $("#body").value : state.session.body,
      method: state.picked,
      should: state.session.should,
      should_not: state.session.should_not,
      depth: {
        nested: !!$("#depth-nested")?.checked,
        tools: !!$("#depth-tools")?.checked,
        scripts: !!$("#depth-scripts")?.checked,
      },
      continue_to_prove: !!continueToProve,
    };
  }

  function renderProve() {
    mount("tpl-prove");
    $("#when").value = state.session.when || "";
    $("#not-when").value = state.session.not_when || "";
    $("#should").value = (state.session.should || []).join("\n");
    $("#should-not").value = (state.session.should_not || []).join("\n");
    paintBench();
    $("#prove-continue").disabled = !state.session.proved;
    $("#run-prove").addEventListener("click", () => runProve(false));
    $("#prove-continue").addEventListener("click", () => runProve(true));
  }

  async function runProve(continueToDispose) {
    const err = $("#prove-error");
    if (err) err.hidden = true;
    try {
      state.session = await api(`/api/sessions/${state.session.id}/prove`, {
        method: "POST",
        body: JSON.stringify({
          when: $("#when").value,
          not_when: $("#not-when").value,
          should: lines($("#should").value),
          should_not: lines($("#should-not").value),
          continue_to_dispose: continueToDispose,
        }),
      });
      if (continueToDispose) return render();
      paintBench();
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

  function paintBench() {
    const box = $("#bench");
    if (!box) return;
    box.replaceChildren();
    (state.session.benchmarks || []).forEach((row) => {
      const card = document.createElement("article");
      card.className = "bench-card";
      const kind = row.badge === "SHOULD WAKE" ? "should" : row.badge === "SHOULD NOT" ? "should-not" : "fail";
      card.innerHTML = `
        <span class="badge badge-${kind}"></span>
        <p class="prompt"></p>
        <p class="verdict"></p>
        <p class="why"></p>
        <p class="teach"></p>`;
      card.querySelector(".badge").textContent = row.badge;
      card.querySelector(".prompt").textContent = `“${row.prompt}”`;
      card.querySelector(".verdict").textContent = row.verdict;
      card.querySelector(".why").textContent = row.why;
      card.querySelector(".teach").textContent = row.teach;
      box.appendChild(card);
    });
  }

  function renderDispose() {
    mount("tpl-dispose");
    paintPack($("#dispose-pack"), state.session);
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

  function renderDoneKeep() {
    mount("tpl-done-keep");
    paintPack($("#kept-pack"), state.session);
    $("#keep-path").textContent = state.session.written_path || "";
    $("#open-skill").addEventListener("click", () => {
      window.open(`/api/sessions/${state.session.id}/skill`, "_blank");
    });
    $("#keep-done").addEventListener("click", reset);
  }

  function renderDoneThrow() {
    mount("tpl-done-throw");
    $("#throw-done").addEventListener("click", reset);
  }

  function reset() {
    state.session = null;
    state.picked = "description";
    state.screen = "start";
    renderStart();
  }

  async function boot() {
    try {
      state.methods = await api("/api/methods");
    } catch {
      state.methods = {
        citation: {
          url: "https://academy.claude.com/tutorials/the-4-ds-of-ai-fluency-behavioral-indicators",
          label: "Cited: Anthropic Academy · Fluency 4Ds — Delegation · Description · Discernment · Diligence (cite only; no invented method prose).",
        },
        methods: [
          { id: "delegation", name: "Delegation", card: "What the agent owns vs what stays with you" },
          { id: "description", name: "Description", card: "Plain job + when / not-when trigger craft" },
          { id: "discernment", name: "Discernment", card: "Checks, near-misses, refuse paths" },
          { id: "diligence", name: "Diligence", card: "Verify steps · more in references/" },
        ],
      };
    }
    renderStart();
  }

  boot();
})();
