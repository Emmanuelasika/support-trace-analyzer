const stages = {
  raw: {
    file: "customer-evidence.json",
    status: "UNSAFE INPUT",
    className: "status-red",
    code: `<span class="tok-muted">{</span>
  <span class="tok-key">"summary"</span>: <span class="tok-string">"POST /v1/messages returned 429"</span>,
  <span class="tok-key">"status_code"</span>: <span class="tok-number">429</span>,
  <span class="tok-key">"request_id"</span>: <span class="tok-string">"req_demo_123"</span>,
  <span class="tok-key">"latency_ms"</span>: <span class="tok-number">214</span>,
  <span class="tok-key">"environment"</span>: <span class="tok-string">"production"</span>,
  <span class="tok-key">"headers"</span>: {
    <span class="tok-key">"retry-after"</span>: <span class="tok-string">"2"</span>
  },
  <span class="tok-key">"body"</span>: <span class="tok-danger">"Authorization: Bearer sk-demo-secret"</span>
<span class="tok-muted">}</span>`,
    note: `<span class="note-number">Stage 01 / intake</span><h3>Useful evidence.<br>Unsafe shape.</h3><p>The status, latency, request ID and retry instruction belong in the investigation. The credential does not. Forwarding this payload would expand the incident.</p><ul><li>429 response captured</li><li>Retry-After: 2 seconds</li><li>Bearer credential exposed</li></ul>`
  },
  safe: {
    file: "safe-evidence.json",
    status: "REDACTED",
    className: "status-green",
    code: `<span class="tok-muted">{</span>
  <span class="tok-key">"summary"</span>: <span class="tok-string">"POST /v1/messages returned 429"</span>,
  <span class="tok-key">"status_code"</span>: <span class="tok-number">429</span>,
  <span class="tok-key">"request_id"</span>: <span class="tok-string">"req_demo_123"</span>,
  <span class="tok-key">"latency_ms"</span>: <span class="tok-number">214</span>,
  <span class="tok-key">"environment"</span>: <span class="tok-string">"production"</span>,
  <span class="tok-key">"headers"</span>: {
    <span class="tok-key">"retry-after"</span>: <span class="tok-string">"2"</span>
  },
  <span class="tok-key">"body"</span>: <span class="tok-string">"Authorization: Bearer [REDACTED]"</span>
<span class="tok-muted">}</span>`,
    note: `<span class="note-number">Stage 02 / trust boundary</span><h3>The signal remains.<br>The secret does not.</h3><p>Recursive redaction handles nested mappings, lists and strings before a diagnosis object exists. The source file remains untouched.</p><ul><li>Credential pattern removed</li><li>Evidence contract validated</li><li>Safe copy ready for analysis</li></ul>`
  },
  diagnosis: {
    file: "incident.md",
    status: "REVIEW REQUIRED",
    className: "status-amber",
    code: `<span class="tok-muted"># Incident bundle 7b4755b5ccd192b9</span>

<span class="tok-key">Classification</span>  <span class="tok-string">rate_limit</span>
<span class="tok-key">Severity</span>        <span class="tok-number">P2</span>
<span class="tok-key">Confidence</span>      <span class="tok-string">high</span>

<span class="tok-muted">## Recommended actions</span>
1. Honor <span class="tok-string">Retry-After</span> when present.
2. Use bounded exponential backoff with jitter.
3. Measure concurrency before requesting a limit change.

<span class="tok-muted">## Escalate when</span>
The failure remains reproducible after recommended actions.`,
    note: `<span class="note-number">Stage 03 / handoff</span><h3>A narrower claim.<br>A better next move.</h3><p>The rules classify the failure family without pretending to know the root cause. The artifact is designed to be reviewed, edited and attached to an engineering escalation.</p><ul><li>rate_limit · P2 · high</li><li>Safe fingerprint created</li><li>Reproduction + escalation threshold</li></ul>`
  }
};

const code = document.querySelector("#trace-code");
const file = document.querySelector("#stage-file");
const status = document.querySelector("#stage-status");
const notes = document.querySelector("#stage-notes");
const pane = document.querySelector(".code-pane");
const tabs = [...document.querySelectorAll("[data-stage]")];

function showStage(name) {
  const stage = stages[name];
  code.innerHTML = stage.code;
  file.textContent = stage.file;
  status.textContent = stage.status;
  status.className = `status ${stage.className}`;
  notes.innerHTML = stage.note;
  tabs.forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.stage === name)));
  pane.classList.remove("is-scanning");
  requestAnimationFrame(() => pane.classList.add("is-scanning"));
}

tabs.forEach((tab, index) => {
  tab.addEventListener("click", () => showStage(tab.dataset.stage));
  tab.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    event.preventDefault();
    const delta = event.key === "ArrowRight" ? 1 : -1;
    const next = tabs[(index + delta + tabs.length) % tabs.length];
    next.focus();
    showStage(next.dataset.stage);
  });
});

showStage("raw");
