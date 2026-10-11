// NormaHub Local Engine UI Frontend Logic

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  loadModels();
  loadStats();
  initArena();
  initVideoStudio();
  initCodeExport();
});

// Tab Switcher
function initTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const target = document.getElementById(`tab-${btn.dataset.tab}`);
      if (target) target.classList.add("active");
    });
  });
}

// Load Models into Selectors
async function loadModels() {
  try {
    const res = await fetch("/v1/models");
    const data = await res.json();
    const models = data.data || [];

    const selectA = document.getElementById("model-a-select");
    const selectB = document.getElementById("model-b-select");

    selectA.innerHTML = "";
    selectB.innerHTML = "";

    models.forEach((m) => {
      const optA = new Option(`${m.id} (${m.owned_by || ""})`, m.id);
      const optB = new Option(`${m.id} (${m.owned_by || ""})`, m.id);
      selectA.add(optA);
      selectB.add(optB);
    });

    selectA.value = "claude-sonnet-5-5";
    selectB.value = "gpt-6-sol";
  } catch (err) {
    console.error("Failed to load models:", err);
  }
}

// Load FinOps & Cache Stats
async function loadStats() {
  try {
    const res = await fetch("/v1/cache/stats");
    const stats = await res.json();

    document.getElementById("stat-total-requests").innerText = stats.total_requests;
    document.getElementById("stat-cache-hits").innerText = stats.cache_hits;
    document.getElementById("stat-hit-rate").innerText = `${stats.hit_rate_pct}%`;
    document.getElementById("stat-rubles-saved").innerText = `${stats.rubles_saved} ₽`;
    document.getElementById("rubles-saved-badge").innerText = `${stats.rubles_saved} ₽`;
  } catch (err) {
    console.error("Failed to load stats:", err);
  }
}

// Arena Duel Execution
function initArena() {
  const runBtn = document.getElementById("arena-run-btn");
  const promptInput = document.getElementById("arena-prompt");

  runBtn.addEventListener("click", async () => {
    const prompt = promptInput.value.trim();
    if (!prompt) {
      alert("Пожалуйста, введите промпт.");
      return;
    }

    const modelA = document.getElementById("model-a-select").value;
    const modelB = document.getElementById("model-b-select").value;

    const outA = document.getElementById("output-a");
    const outB = document.getElementById("output-b");
    const ttftA = document.getElementById("ttft-a");
    const ttftB = document.getElementById("ttft-b");
    const costA = document.getElementById("cost-a");
    const costB = document.getElementById("cost-b");

    outA.innerText = "Стриминг токенов...";
    outB.innerText = "Стриминг токенов...";
    ttftA.innerText = "Замер...";
    ttftB.innerText = "Замер...";

    runModelRequest(modelA, prompt, outA, ttftA, costA);
    runModelRequest(modelB, prompt, outB, ttftB, costB);
  });

  document.getElementById("clear-cache-btn").addEventListener("click", async () => {
    if (confirm("Вы уверены, что хотите очистить локальный кэш?")) {
      await fetch("/v1/cache/clear", { method: "POST" });
      loadStats();
      alert("Локальный кэш очищен.");
    }
  });
}

async function runModelRequest(model, prompt, outputElem, ttftElem, costElem) {
  const startTime = performance.now();
  let firstTokenReceived = false;

  try {
    const res = await fetch("/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        messages: [{ role: "user", content: prompt }],
      }),
    });

    const data = await res.json();
    const elapsed = Math.round(performance.now() - startTime);
    ttftElem.innerText = `${elapsed} ms`;

    if (data.choices && data.choices[0]) {
      outputElem.innerText = data.choices[0].message.content;
      const tokens = data.usage?.total_tokens || 0;
      costElem.innerText = `~${tokens} токенов`;
    } else if (data.error) {
      outputElem.innerText = `Ошибка: ${data.error.message || JSON.stringify(data.error)}`;
    }

    loadStats();
  } catch (err) {
    outputElem.innerText = `Ошибка сети: ${err.message}`;
  }
}

// Video Studio
function initVideoStudio() {
  const generateBtn = document.getElementById("video-generate-btn");
  const promptInput = document.getElementById("video-prompt");
  const modelSelect = document.getElementById("video-model-select");
  const durationSelect = document.getElementById("video-duration-select");
  const statusBox = document.getElementById("video-status-box");
  const statusText = document.getElementById("video-status-text");
  const resultBox = document.getElementById("video-result-box");
  const player = document.getElementById("video-player");
  const downloadLink = document.getElementById("video-download-link");

  generateBtn.addEventListener("click", async () => {
    const prompt = promptInput.value.trim();
    if (!prompt) {
      alert("Введите описание сцены.");
      return;
    }

    statusBox.classList.remove("hidden");
    resultBox.classList.add("hidden");
    statusText.innerText = "Отправка задачи в NormaHub Video Gateway...";
    generateBtn.disabled = true;

    try {
      const res = await fetch("/v1/videos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          model: modelSelect.value,
          duration: parseInt(durationSelect.value, 10),
        }),
      });

      const task = await res.json();
      if (!task.id) throw new Error(task.error?.message || "Не получен task ID");

      statusText.innerText = `Задача #${task.id} принята. Ожидание рендера нейросетью...`;

      // Poll
      const pollInterval = setInterval(async () => {
        try {
          const pollRes = await fetch(`/v1/videos/status/${task.id}`);
          const current = await pollRes.json();

          if (current.status === "completed" && current.video_url) {
            clearInterval(pollInterval);
            statusBox.classList.add("hidden");
            resultBox.classList.remove("hidden");
            player.src = current.video_url;
            downloadLink.href = current.video_url;
            generateBtn.disabled = false;
          } else if (current.status === "failed") {
            clearInterval(pollInterval);
            statusText.innerText = `Ошибка рендера: ${current.error || "Неизвестная ошибка"}`;
            generateBtn.disabled = false;
          } else {
            statusText.innerText = `Статус задачи: ${current.status.toUpperCase()} (рендеринг кадров)...`;
          }
        } catch (e) {
          console.error("Poll error", e);
        }
      }, 4000);

    } catch (err) {
      statusText.innerText = `Ошибка: ${err.message}`;
      generateBtn.disabled = false;
    }
  });
}

// Code Exporter
function initCodeExport() {
  const snippetBox = document.getElementById("exported-code-snippet");
  const tabs = document.querySelectorAll(".code-tab-btn");

  const snippets = {
    python: `from openai import OpenAI

# NormaHub Local Gateway (0ms cache, Pareto router, No VPN)
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="nr_hub_local"
)

response = client.chat.completions.create(
    model="normahub/auto",  # Авто-роутер Pareto
    messages=[{"role": "user", "content": "Привет! Напиши FastAPI сервис."}]
)
print(response.choices[0].message.content)`,

    ts: `import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "http://localhost:8000/v1",
  apiKey: "nr_hub_local",
});

const completion = await client.chat.completions.create({
  model: "claude-sonnet-5-5",
  messages: [{ role: "user", content: "Привет!" }],
});
console.log(completion.choices[0].message.content);`,

    curl: `curl http://localhost:8000/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "normahub/auto",
    "messages": [{"role": "user", "content": "Привет!"}]
  }'`,
  };

  function updateCode(lang) {
    snippetBox.innerText = snippets[lang] || snippets.python;
  }

  tabs.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabs.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      updateCode(btn.dataset.lang);
    });
  });

  updateCode("python");
}
