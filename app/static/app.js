(() => {
  const STEPS = {
    intent: "Step 1 · Intent",
    methods: "Step 2 · Methods",
    prove: "Step 3 · Prove trigger",
    fill: "Step 4 · Fill section",
    preview: "Step 5 · Preview · dispose",
    done_accept: "Done · Accept",
    done_reject: "Done · Reject",
  };

  const D_NAMES = {
    delegation: "Delegation",
    description: "Description",
    discernment: "Discernment",
    diligence: "Diligence",
  };

  const state = {
    session: null,
    methods: null,
    picked: null,
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const app = $("#app");
  const navStep = $("#nav-step");

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

  function busy(btn, on) {
    if (!btn) return;
    btn.disabled = on;
  }

  function render() {
    const step = state.session?.step || "intent";
    navStep.textContent = STEPS[step] || STEPS.intent;
    if (step === "intent" || !state.session) return renderIntent();
    if (step === "methods") return renderMethods();
    if (step === "prove") return renderProve();
    if (step === "fill") return renderFill();
    if (step === "preview") return renderPreview();
    if (step === "done_accept") return renderDoneAccept();
    if (step === "done_reject") return renderDoneReject();
  }

  function renderIntent() {
    mount("tpl-intent");
    const ta = $("#intent");
    if (state.session?.intent) ta.value = state.session.intent;
    $("#intent-continue").addEventListener("click", async (e) => {
      const intent = ta.value.trim();
      if (!intent) {
        ta.focus();
        return;
      }
      busy(e.currentTarget, true);
      try {
        state.session = await api("/api/sessions", {
          method: "POST",
          body: JSON.stringify({ intent }),
        });
        render();
      } catch (err) {
        alert(err.message);
        busy(e.currentTarget, false);
      }
    });
  }

  function renderMethods() {
    mount("tpl-methods");
    const cards = $("#method-cards");
    const methods = state.methods?.methods || [];
    const cite = state.methods?.citation;
    if (cite) {
      const a = $("#academy-cite");
      a.href = cite.url;
      a.textContent = cite.label;
    }
    if (!state.picked && state.session?.method) state.picked = state.session.method;
    methods.forEach((m) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "card" + (state.picked === m.id ? " sel" : "");
      btn.innerHTML = `<strong>${m.name}</strong><span>${m.card}</span>`;
      btn.addEventListener("click", () => {
        state.picked = m.id;
        renderMethods();
      });
      cards.appendChild(btn);
    });
    $("#methods-continue").addEventListener("click", async (e) => {
      if (!state.picked) return;
      busy(e.currentTarget, true);
      try {
        state.session = await api(`/api/sessions/${state.session.id}/method`, {
          method: "POST",
          body: JSON.stringify({ method: state.picked }),
        });
        render();
      } catch (err) {
        alert(err.message);
        busy(e.currentTarget, false);
      }
    });
  }

  function renderProve() {
    mount("tpl-prove");
    $("#when").value = state.session.when || "";
    $("#not-when").value = state.session.not_when || "";
    paintPrompts();
    if (!state.session.should.length && !state.session.should_not.length) {
      refreshPrompts();
    }
    $("#prove-continue").addEventListener("click", async (e) => {
      const when = $("#when").value.trim();
      const notWhen = $("#not-when").value.trim();
      if (!when || !notWhen) {
        alert("When and Not when must be non-empty.");
        return;
      }
      busy(e.currentTarget, true);
      try {
        state.session = await api(`/api/sessions/${state.session.id}/prove`, {
          method: "POST",
          body: JSON.stringify({
            when,
            not_when: notWhen,
            should: state.session.should,
            should_not: state.session.should_not,
            continue_to_fill: true,
          }),
        });
        render();
      } catch (err) {
        alert(err.message);
        busy(e.currentTarget, false);
      }
    });
  }

  async function refreshPrompts() {
    const when = $("#when")?.value || state.session.when;
    const notWhen = $("#not-when")?.value || state.session.not_when;
    state.session = await api(`/api/sessions/${state.session.id}/prove`, {
      method: "POST",
      body: JSON.stringify({ when, not_when: notWhen }),
    });
    paintPrompts();
  }

  function paintPrompts() {
    const box = $("#prompts");
    if (!box) return;
    box.replaceChildren();
    (state.session.should || []).forEach((t) => box.appendChild(promptRow("should", t)));
    (state.session.should_not || []).forEach((t) => box.appendChild(promptRow("should-not", t)));
  }

  function promptRow(kind, text) {
    const row = document.createElement("div");
    row.className = "prompt";
    const tag = kind === "should" ? "tag-should" : "tag-should-not";
    row.innerHTML = `<span class="tag ${tag}">${kind}</span><span></span>`;
    row.lastChild.textContent = `“${text}”`;
    return row;
  }

  function renderFill() {
    mount("tpl-fill");
    const current = state.session.current_d;
    const name = D_NAMES[current] || current;
    $("#fill-title").textContent = `Fill · ${name}`;
    $("#draft-kicker").textContent = `${name.toUpperCase()} (draft)`;
    const sec = state.session.sections[current] || {};
    $("#draft-body").textContent = sec.body || "—";
    const chips = $("#d-chips");
    (state.session.order || Object.keys(D_NAMES)).forEach((id) => {
      const chip = document.createElement("span");
      chip.className = "chip" + (id === current ? " on" : "");
      chip.textContent = D_NAMES[id] || id;
      chips.appendChild(chip);
    });
    $("#fill-skip").addEventListener("click", () => fillAction("skip"));
    $("#fill-regen").addEventListener("click", () => fillAction("regen"));
    $("#fill-continue").addEventListener("click", () => fillAction("continue"));
  }

  async function fillAction(action) {
    try {
      state.session = await api(`/api/sessions/${state.session.id}/fill`, {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      render();
    } catch (err) {
      alert(err.message);
    }
  }

  function renderPreview() {
    mount("tpl-preview");
    const card = $("#preview-card");
    const whenSec = sectionBlock("WHEN · NOT WHEN", null,
      `When: ${state.session.when}\nNot when: ${state.session.not_when}`);
    card.appendChild(whenSec);
    (state.session.preview || []).forEach((sec) => {
      card.appendChild(sectionBlock(sec.name.toUpperCase(), sec.badge, sec.body, !!sec.badge));
    });
    const blocked = !state.session.when.trim() || !state.session.not_when.trim();
    const accept = $("#accept");
    const err = $("#preview-error");
    if (blocked) {
      accept.disabled = true;
      err.hidden = false;
      err.textContent = "Accept blocked: When and Not when must be non-empty.";
    }
    accept.addEventListener("click", async () => {
      if (blocked) return;
      try {
        state.session = await api(`/api/sessions/${state.session.id}/accept`, { method: "POST" });
        render();
      } catch (e) {
        err.hidden = false;
        err.textContent = e.message;
      }
    });
    $("#reject").addEventListener("click", async () => {
      try {
        state.session = await api(`/api/sessions/${state.session.id}/reject`, { method: "POST" });
        render();
      } catch (e) {
        err.hidden = false;
        err.textContent = e.message;
      }
    });
  }

  function sectionBlock(title, badge, body, muted) {
    const el = document.createElement("div");
    el.className = "sec";
    const head = document.createElement("div");
    head.className = "sec-head";
    const h = document.createElement("h3");
    h.textContent = title;
    head.appendChild(h);
    if (badge) {
      const b = document.createElement("span");
      b.className = "badge badge-skip";
      b.textContent = badge;
      head.appendChild(b);
    }
    const p = document.createElement("p");
    p.className = muted ? "muted" : "";
    p.textContent = body;
    el.append(head, p);
    return el;
  }

  function renderDoneAccept() {
    mount("tpl-done-accept");
    $("#accept-path").textContent = state.session.written_path || "";
    $("#open-folder").addEventListener("click", () => {
      window.open(`/api/sessions/${state.session.id}/skill`, "_blank");
    });
    $("#accept-done").addEventListener("click", reset);
  }

  function renderDoneReject() {
    mount("tpl-done-reject");
    $("#start-over").addEventListener("click", reset);
    $("#reject-done").addEventListener("click", reset);
  }

  function reset() {
    state.session = null;
    state.picked = null;
    render();
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
    render();
  }

  boot();
})();
