// frontend/static/script.js

const $ = (id) => document.getElementById(id);

let currentModel = null;   // fitted model (GMF as a JS object)
let currentCsv = null;     // last generated synthetic data (CSV text)

// ---------- helpers ----------

function setMessage(el, text, kind = "") {
    el.textContent = text;
    el.className = "message" + (kind ? " " + kind : "");
}

function setBusy(button, busy, busyLabel) {
    if (busy) {
        button.dataset.label = button.textContent;
        button.textContent = busyLabel;
    } else if (button.dataset.label) {
        button.textContent = button.dataset.label;
    }
    button.disabled = busy;
}

async function postAndParse(url, options) {
    const response = await fetch(url, options);
    let data;
    try {
        data = await response.json();
    } catch {
        throw new Error(`Unexpected response from server (${response.status}).`);
    }
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
    return data;
}

function download(filename, text, mime) {
    const url = URL.createObjectURL(new Blob([text], { type: mime }));
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// Small CSV parser that handles quoted fields.
function parseCsv(text) {
    const rows = [];
    let row = [], field = "", inQuotes = false;
    for (let i = 0; i < text.length; i++) {
        const c = text[i];
        if (inQuotes) {
            if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
            else if (c === '"') inQuotes = false;
            else field += c;
        } else if (c === '"') inQuotes = true;
        else if (c === ",") { row.push(field); field = ""; }
        else if (c === "\n" || c === "\r") {
            if (c === "\r" && text[i + 1] === "\n") i++;
            row.push(field); field = "";
            rows.push(row); row = [];
        } else field += c;
    }
    if (field !== "" || row.length) { row.push(field); rows.push(row); }
    return rows;
}

function fillRow(parent, cells, tag) {
    const tr = document.createElement("tr");
    cells.forEach((value) => {
        const cell = document.createElement(tag);
        cell.textContent = value;
        tr.appendChild(cell);
    });
    parent.appendChild(tr);
}

// ---------- API status ----------

async function checkApi() {
    const badge = $("apiStatus");
    try {
        const response = await fetch("/get_welcome_message");
        if (!response.ok) throw new Error();
        badge.textContent = "API connected";
        badge.className = "up";
    } catch {
        badge.textContent = "API not reachable – start it with: uvicorn main:app --reload";
        badge.className = "down";
    }
}

// ---------- step 1: fit model ----------

function showModel(model, sourceName) {
    currentModel = model;
    currentCsv = null;
    $("synthResult").hidden = true;

    const vars = Array.isArray(model.vars) ? model.vars : [];
    const body = $("modelBody");
    body.replaceChildren();
    vars.forEach((v) => {
        const type = v.type || v.dtype || "";
        const dist = (v.distribution && (v.distribution.implements || v.distribution.name)) || "";
        fillRow(body, [v.name ?? "", type, dist], "td");
    });

    const rowInfo = Number.isInteger(model.n_rows) ? `${model.n_rows} rows, ` : "";
    $("modelCaption").textContent = `${sourceName}: ${rowInfo}${vars.length} columns`;
    $("fitResult").hidden = false;

    // Unlock step 2
    $("synthPanel").classList.remove("locked");
    $("numRows").disabled = false;
    $("synthButton").disabled = false;
    $("numRows").placeholder = Number.isInteger(model.n_rows) ? `Same as original (${model.n_rows})` : "100";
}

$("fitForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const file = $("dataFile").files[0];
    if (!file) {
        setMessage($("fitMessage"), "Choose a CSV or TSV file first.", "error");
        return;
    }
    const button = $("fitButton");
    setBusy(button, true, "Fitting…");
    setMessage($("fitMessage"), "");
    try {
        const form = new FormData();
        form.append("file", file);
        const data = await postAndParse("/api/fit-model", { method: "POST", body: form });
        showModel(data.model_json, file.name);
        setMessage($("fitMessage"), "Model fitted.", "ok");
    } catch (err) {
        setMessage($("fitMessage"), err.message, "error");
    } finally {
        setBusy(button, false);
    }
});

$("downloadModel").addEventListener("click", () => {
    if (currentModel) download("model.json", JSON.stringify(currentModel, null, 2), "application/json");
});

// ---------- step 2: synthesize ----------

$("modelFile").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
        const model = JSON.parse(await file.text());
        if (typeof model !== "object" || model === null || Array.isArray(model)) throw new Error();
        showModel(model, file.name);
        setMessage($("synthMessage"), "Model loaded.", "ok");
    } catch {
        setMessage($("synthMessage"), "That file is not a valid model JSON.", "error");
    }
});

$("synthForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentModel) return;

    const payload = { model_json: currentModel };
    const rows = $("numRows").value.trim();
    if (rows) {
        const n = Number(rows);
        if (!Number.isInteger(n) || n < 1) {
            setMessage($("synthMessage"), "Enter a whole number of rows, 1 or more.", "error");
            return;
        }
        payload.num_rows = n;
    }

    const button = $("synthButton");
    setBusy(button, true, "Generating…");
    setMessage($("synthMessage"), "");
    try {
        const data = await postAndParse("/api/synthesize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        currentCsv = data.synthetic_data_csv;
        renderPreview(currentCsv);
        setMessage($("synthMessage"), "Synthetic data generated.", "ok");
    } catch (err) {
        setMessage($("synthMessage"), err.message, "error");
    } finally {
        setBusy(button, false);
    }
});

function renderPreview(csv) {
    const rows = parseCsv(csv.trim());
    const [header = [], ...data] = rows;
    const PREVIEW = 10;

    const head = $("synthHead"), body = $("synthBody");
    head.replaceChildren();
    body.replaceChildren();
    fillRow(head, header, "th");
    data.slice(0, PREVIEW).forEach((r) => fillRow(body, r, "td"));

    $("synthCaption").textContent =
        `${data.length} rows generated – showing the first ${Math.min(PREVIEW, data.length)}`;
    $("synthResult").hidden = false;
}

$("downloadCsv").addEventListener("click", () => {
    if (currentCsv) download("synthetic.csv", currentCsv, "text/csv");
});

// ---------- init ----------

document.addEventListener("DOMContentLoaded", checkApi);