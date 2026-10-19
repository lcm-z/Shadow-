const welcome = document.querySelector("#welcome");
const dashboard = document.querySelector("#dashboard");
const loading = document.querySelector("#loading-overlay");
const analyzeButton = document.querySelector("#analyze-button");
const refreshButton = document.querySelector("#refresh-button");
const closeAppButton = document.querySelector("#close-app-button");
const liveToggleButton = document.querySelector("#live-toggle");
const chart = document.querySelector("#resource-chart");
const chartContext = chart.getContext("2d");

let latestReport = null;
let chartFrame = 0;
let liveTimer = null;
let liveRequestBusy = false;
let currentOptimizerOverview = null;

analyzeButton.addEventListener("click", async () => {
  welcome.classList.add("hidden");
  dashboard.classList.remove("hidden");
  await analyze();
});

refreshButton.addEventListener("click", analyze);
closeAppButton.addEventListener("click", () => {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.close_app();
  }
});
document.querySelector("#process-list").addEventListener("click", handleProcessAction);
document.querySelector("#cleanup-button").addEventListener("click", cleanupTempFiles);
document.querySelector("#cleanup-files").addEventListener("change", updateCleanupSelection);
document.querySelector("#startup-list").addEventListener("click", handleStartupAction);
document.querySelector("#power-plan-button").addEventListener("click", activateSelectedPowerPlan);
document.querySelector("#power-plan-select").addEventListener("change", updatePowerDescription);
liveToggleButton.addEventListener("click", toggleLiveMonitoring);
window.addEventListener("resize", drawChart);
window.addEventListener("pywebviewready", () => {
  document.body.classList.add("desktop-ready");
});

async function analyze() {
  if (liveTimer) toggleLiveMonitoring();
  loading.classList.remove("hidden");
  refreshButton.disabled = true;
  liveToggleButton.disabled = true;
  showError("");
  try {
    latestReport = await window.pywebview.api.scan();
    renderReport(latestReport);
    await loadOptimizerOverview();
    loading.classList.add("hidden");
  } catch (error) {
    loading.classList.add("hidden");
    showError(`Não foi possível analisar o computador: ${error.message || error}`);
  } finally {
    refreshButton.disabled = false;
    liveToggleButton.disabled = !latestReport;
  }
}

function renderReport(report) {
  const memory = report.memory;
  setText("cpu-value", `${report.cpu_percent.toFixed(1)}%`);
  setText("ram-value", `${memory.used_percent.toFixed(1)}%`);
  setText("available-value", `${memory.available_gb.toFixed(1)} GB`);
  setText("ram-total", `Memória total: ${memory.total_gb.toFixed(2)} GB`);
  setWidth("cpu-meter", report.cpu_percent);
  setWidth("ram-meter", memory.used_percent);

  const status = document.querySelector("#system-status");
  status.classList.add("ready");
  status.innerHTML = `<span class="status-dot"></span>${escapeHtml(report.system.name)} ${escapeHtml(report.system.release)} · análise concluída`;

  const level = report.diagnosis.level;
  const badge = document.querySelector("#level-badge");
  badge.textContent = `NÍVEL ${level}`;
  badge.className = `level-badge ${level === "ALTO" ? "high" : level === "MÉDIO" ? "medium" : ""}`;
  setText("diagnosis-text", `${report.diagnosis.message} Este diagnóstico é preliminar e não mede desempenho em jogos.`);

  const processList = document.querySelector("#process-list");
  processList.replaceChildren();
  for (const process of report.top_ram_processes.slice(0, 5)) {
    const row = document.createElement("li");
    row.className = "process-row";
    const name = document.createElement("span");
    name.className = "process-name";
    const usage = document.createElement("span");
    usage.className = "process-usage";
    name.textContent = `${process.name} · PID ${process.pid}`;
    usage.textContent = `${process.ram_mb.toFixed(0)} MB`;
    const closeButton = document.createElement("button");
    closeButton.className = "process-close-button";
    closeButton.type = "button";
    closeButton.textContent = "Encerrar";
    closeButton.setAttribute("aria-label", `Encerrar ${process.name}`);
    closeButton.dataset.pid = process.pid;
    closeButton.dataset.name = process.name;
    closeButton.dataset.createTime = process.create_time;
    row.append(name, usage, closeButton);
    processList.append(row);
  }

  const recommendationList = document.querySelector("#recommendation-list");
  recommendationList.replaceChildren();
  for (const recommendation of report.recommendations) {
    const item = document.createElement("li");
    item.textContent = recommendation;
    recommendationList.append(item);
  }

  setText("platform-note", report.system.is_windows
    ? "Análise informativa; não mede FPS de jogos."
    : "Modo de desenvolvimento no Linux; sistema-alvo: Windows 10/11.");
  drawChart();
  animateChart();
}

async function loadOptimizerOverview() {
  try {
    currentOptimizerOverview = await window.pywebview.api.optimizer_overview();
    renderDisks(currentOptimizerOverview.disks || []);
    renderTempPreview(currentOptimizerOverview.temp_cleanup || {});
    renderStartup(currentOptimizerOverview.startup || {});
    renderPowerPlans(currentOptimizerOverview.power_plans || {});
  } catch (error) {
    showNotice(`Não foi possível carregar as ferramentas: ${error.message || error}`, "warning");
  }
}

function renderDisks(disks) {
  const list = document.querySelector("#disk-list");
  list.replaceChildren();
  if (!disks.length) {
    appendEmpty(list, "Nenhuma unidade acessível foi encontrada.");
    return;
  }
  for (const disk of disks) {
    const row = document.createElement("li");
    row.className = "disk-row";
    const name = document.createElement("span");
    name.className = "disk-row-name";
    name.textContent = `${disk.name} · ${disk.used_percent.toFixed(0)}% usado`;
    const free = document.createElement("span");
    free.className = "disk-row-free";
    free.textContent = `${disk.free_gb.toFixed(1)} GB livres`;
    const meter = document.createElement("div");
    meter.className = "disk-meter";
    const fill = document.createElement("span");
    fill.style.width = `${Math.min(100, disk.used_percent)}%`;
    meter.append(fill);
    row.append(name, free, meter);
    list.append(row);
  }
}

function renderTempPreview(preview) {
  const summary = document.querySelector("#cleanup-summary");
  const button = document.querySelector("#cleanup-button");
  const list = document.querySelector("#cleanup-files");
  list.replaceChildren();
  button.textContent = "Limpar temporários selecionados";
  if (!preview.supported) {
    summary.textContent = preview.message || "Disponível na versão Windows.";
    button.disabled = true;
    appendEmpty(list, "Nenhuma alteração foi feita.");
    return;
  }
  summary.textContent = `${preview.file_count} arquivo(s) com mais de ${preview.minimum_age_days} dias · até ${formatBytes(preview.bytes)}. Revise a lista e desmarque o que quiser manter.`;
  button.disabled = preview.file_count === 0;
  if (!preview.files.length) {
    button.textContent = "Nenhum temporário antigo";
    appendEmpty(list, preview.file_count ? "Arquivos antigos encontrados." : "Nenhum temporário antigo encontrado.");
    return;
  }
  for (const file of preview.files) {
    const item = document.createElement("li");
    item.className = "cleanup-file-row";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;
    checkbox.dataset.path = file.path;
    checkbox.setAttribute("aria-label", `Selecionar ${file.path} para limpeza`);
    const filename = document.createElement("span");
    filename.className = "cleanup-file";
    filename.textContent = file.path;
    filename.title = file.path;
    const size = document.createElement("span");
    size.className = "cleanup-file-size";
    size.textContent = formatBytes(file.bytes);
    item.append(checkbox, filename, size);
    list.append(item);
  }
  updateCleanupSelection();
}

function renderStartup(data) {
  const scope = document.querySelector("#startup-scope");
  const list = document.querySelector("#startup-list");
  list.replaceChildren();
  if (!data.supported) {
    scope.textContent = data.message || "Disponível na versão Windows.";
    appendEmpty(list, "Nenhuma configuração foi alterada.");
    return;
  }
  scope.textContent = data.scope;
  if (!data.items.length) {
    appendEmpty(list, "Nenhum item nesta lista da sua conta.");
    return;
  }
  for (const startup of data.items) {
    const row = document.createElement("li");
    row.className = "startup-row";
    const text = document.createElement("span");
    text.className = "startup-text";
    const name = document.createElement("span");
    name.className = "startup-name";
    name.textContent = startup.name;
    const command = document.createElement("span");
    command.className = "startup-command";
    command.textContent = startup.command;
    command.title = startup.command;
    text.append(name, command);
    const action = document.createElement("button");
    action.className = "startup-action";
    action.type = "button";
    action.textContent = startup.enabled ? "Desativar" : "Reativar";
    action.dataset.name = startup.name;
    action.dataset.enabled = String(startup.enabled);
    row.append(text, action);
    list.append(row);
  }
}

function renderPowerPlans(data) {
  const select = document.querySelector("#power-plan-select");
  const button = document.querySelector("#power-plan-button");
  select.replaceChildren();
  if (!data.supported || !data.plans.length) {
    select.disabled = true;
    button.disabled = true;
    document.querySelector("#power-description").textContent = data.message || "Nenhum plano disponível.";
    const option = document.createElement("option");
    option.textContent = "Disponível na versão Windows";
    select.append(option);
    return;
  }
  for (const plan of data.plans) {
    const option = document.createElement("option");
    option.value = plan.guid;
    option.textContent = `${plan.name}${plan.active ? " (atual)" : ""}`;
    option.dataset.description = plan.description;
    option.dataset.active = String(plan.active);
    select.append(option);
  }
  select.disabled = false;
  button.disabled = true;
  updatePowerDescription();
}

function updatePowerDescription() {
  const select = document.querySelector("#power-plan-select");
  const option = select.selectedOptions[0];
  if (!option || !currentOptimizerOverview?.power_plans?.supported) return;
  document.querySelector("#power-description").textContent = option.dataset.description;
  document.querySelector("#power-plan-button").disabled = option.dataset.active === "true";
}

async function cleanupTempFiles() {
  const preview = currentOptimizerOverview?.temp_cleanup;
  const selectedPaths = [...document.querySelectorAll("#cleanup-files input:checked")]
    .map(checkbox => checkbox.dataset.path);
  if (!preview?.supported || !selectedPaths.length) return;
  const selectedFiles = preview.files.filter(file => selectedPaths.includes(file.path));
  const selectedBytes = selectedFiles.reduce((total, file) => total + file.bytes, 0);
  const confirmed = window.confirm(
    `Você selecionou ${selectedFiles.length} arquivo(s) temporário(s) com mais de 7 dias.\n` +
    `Tamanho estimado: ${formatBytes(selectedBytes)}.\n\n` +
    "Arquivos em uso serão ignorados. Deseja continuar?"
  );
  if (!confirmed) return;
  const button = document.querySelector("#cleanup-button");
  button.disabled = true;
  try {
    const result = await window.pywebview.api.clean_temp(selectedPaths);
    showNotice(result.message, result.success ? "success" : "warning");
    await loadOptimizerOverview();
  } catch (error) {
    showNotice(`A limpeza não foi concluída: ${error.message || error}`, "warning");
    button.disabled = false;
  }
}

function updateCleanupSelection() {
  const selectedCount = document.querySelectorAll("#cleanup-files input:checked").length;
  const button = document.querySelector("#cleanup-button");
  button.disabled = selectedCount === 0;
  button.textContent = selectedCount
    ? `Limpar ${selectedCount} arquivo(s) selecionado(s)`
    : "Nenhum arquivo selecionado";
}

async function handleStartupAction(event) {
  const button = event.target.closest(".startup-action");
  if (!button) return;
  const enabled = button.dataset.enabled === "true";
  const itemName = button.dataset.name;
  const question = enabled
    ? `Desativar ${itemName} da inicialização da sua conta?\n\nO Shadow guarda uma cópia local para permitir reativar depois.`
    : `Reativar ${itemName} para iniciar quando você entrar no Windows?`;
  if (!window.confirm(question)) return;
  button.disabled = true;
  try {
    const result = await window.pywebview.api.set_startup(itemName, !enabled);
    showNotice(result.message, result.success ? "success" : "warning");
    if (result.success) await loadOptimizerOverview();
    else button.disabled = false;
  } catch (error) {
    showNotice(`Não foi possível alterar a inicialização: ${error.message || error}`, "warning");
    button.disabled = false;
  }
}

async function activateSelectedPowerPlan() {
  const select = document.querySelector("#power-plan-select");
  const option = select.selectedOptions[0];
  if (!option) return;
  if (!window.confirm(`Ativar o plano “${option.textContent}”?\n\nIsso muda o perfil de energia do Windows. Você pode escolher outro plano depois; não há garantia de aumento de FPS.`)) return;
  const button = document.querySelector("#power-plan-button");
  button.disabled = true;
  try {
    const result = await window.pywebview.api.set_power_plan(option.value);
    showNotice(result.message, result.success ? "success" : "warning");
    if (result.success) await loadOptimizerOverview();
    else button.disabled = false;
  } catch (error) {
    showNotice(`Não foi possível alterar o plano: ${error.message || error}`, "warning");
    button.disabled = false;
  }
}

function toggleLiveMonitoring() {
  if (!latestReport) return;
  if (liveTimer) {
    clearInterval(liveTimer);
    liveTimer = null;
    liveToggleButton.textContent = "Iniciar ao vivo";
    document.querySelector("#live-status").classList.add("paused");
    document.querySelector("#live-status").innerHTML = "<i></i> PAUSADO";
    return;
  }
  liveToggleButton.textContent = "Pausar monitoramento";
  document.querySelector("#live-status").classList.remove("paused");
  document.querySelector("#live-status").innerHTML = "<i></i> AO VIVO";
  updateLiveSample();
  liveTimer = setInterval(updateLiveSample, 1000);
}

async function updateLiveSample() {
  if (liveRequestBusy || !window.pywebview?.api) return;
  liveRequestBusy = true;
  try {
    const sample = await window.pywebview.api.live_sample();
    setText("cpu-value", `${sample.cpu_percent.toFixed(1)}%`);
    setText("ram-value", `${sample.ram_percent.toFixed(1)}%`);
    setText("available-value", `${sample.available_gb.toFixed(1)} GB`);
    setWidth("cpu-meter", sample.cpu_percent);
    setWidth("ram-meter", sample.ram_percent);
    setText("disk-read-rate", `${sample.disk_read_mb_s.toFixed(1)} MB/s`);
    setText("disk-write-rate", `${sample.disk_write_mb_s.toFixed(1)} MB/s`);
    latestReport.monitoring.cpu_samples.push(sample.cpu_percent);
    latestReport.monitoring.ram_samples.push(sample.ram_percent);
    latestReport.monitoring.cpu_samples = latestReport.monitoring.cpu_samples.slice(-60);
    latestReport.monitoring.ram_samples = latestReport.monitoring.ram_samples.slice(-60);
    renderLiveProcesses("live-cpu-list", sample.top_cpu_processes, item => `${item.cpu_percent.toFixed(1)}%`);
    renderLiveProcesses("live-ram-list", sample.top_ram_processes, item => `${item.ram_mb.toFixed(0)} MB`);
    drawChart();
  } catch (error) {
    showNotice(`O monitoramento ao vivo parou: ${error.message || error}`, "warning");
    toggleLiveMonitoring();
  } finally {
    liveRequestBusy = false;
  }
}

function renderLiveProcesses(id, processes, valueText) {
  const list = document.getElementById(id);
  list.replaceChildren();
  if (!processes.length) {
    appendEmpty(list, "Sem dados de processos nesta amostra.");
    return;
  }
  for (const process of processes) {
    const row = document.createElement("li");
    row.className = "live-process-row";
    const name = document.createElement("span");
    name.textContent = `${process.name} · PID ${process.pid}`;
    const value = document.createElement("span");
    value.textContent = valueText(process);
    row.append(name, value);
    list.append(row);
  }
}

function appendEmpty(list, message) {
  const item = document.createElement("li");
  item.className = "empty-state";
  item.textContent = message;
  list.append(item);
}

function formatBytes(bytes) {
  if (!bytes) return "0 MB";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index++;
  }
  return `${value.toFixed(index >= 2 ? 1 : 0)} ${units[index]}`;
}

async function handleProcessAction(event) {
  const button = event.target.closest(".process-close-button");
  if (!button) return;

  const processName = button.dataset.name;
  const confirmed = window.confirm(
    `Deseja pedir ao sistema para encerrar ${processName} (PID ${button.dataset.pid})?\n\n` +
    "Isso pode fechar o aplicativo e causar perda de trabalho não salvo. O Shadow não força o encerramento."
  );
  if (!confirmed) return;

  button.disabled = true;
  showNotice("Solicitando o encerramento do aplicativo…", "info");
  try {
    const result = await window.pywebview.api.terminate_process(
      Number(button.dataset.pid),
      processName,
      Number(button.dataset.createTime)
    );
    if (!result.success) {
      showNotice(result.message, "warning");
      button.disabled = false;
      return;
    }

    await analyze();
    showNotice(`${result.message} Os recursos podem levar um tempo para atualizar.`, "success");
  } catch (error) {
    showNotice(`Não foi possível encerrar o processo: ${error.message || error}`, "warning");
    button.disabled = false;
  }
}

function drawChart() {
  const rect = chart.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const scale = window.devicePixelRatio || 1;
  chart.width = Math.round(rect.width * scale);
  chart.height = Math.round(rect.height * scale);
  chartContext.setTransform(scale, 0, 0, scale, 0, 0);
  chartContext.clearRect(0, 0, rect.width, rect.height);

  const left = 38;
  const right = rect.width - 12;
  const top = 14;
  const bottom = rect.height - 18;
  chartContext.font = "10px Segoe UI, Arial, sans-serif";
  chartContext.textAlign = "right";
  chartContext.textBaseline = "middle";
  for (const value of [0, 25, 50, 75, 100]) {
    const y = bottom - (bottom - top) * value / 100;
    chartContext.strokeStyle = "rgba(191, 153, 222, .13)";
    chartContext.lineWidth = 1;
    chartContext.beginPath();
    chartContext.moveTo(left, y);
    chartContext.lineTo(right, y);
    chartContext.stroke();
    chartContext.fillStyle = "#887b98";
    chartContext.fillText(`${value}%`, left - 9, y);
  }
  if (!latestReport) return;
  drawSeries(latestReport.monitoring.cpu_samples, "#bd8aff", left, right, top, bottom);
  drawSeries(latestReport.monitoring.ram_samples, "#ed91ff", left, right, top, bottom);
}

function drawSeries(values, color, left, right, top, bottom) {
  if (!values || values.length === 0) return;
  const span = Math.max(1, right - left);
  const points = values.map((value, index) => ({
    x: left + span * index / Math.max(values.length - 1, 1),
    y: bottom - (bottom - top) * Math.max(0, Math.min(value, 100)) / 100,
  }));

  chartContext.beginPath();
  chartContext.moveTo(points[0].x, points[0].y);
  for (let index = 1; index < points.length; index++) {
    const previous = points[index - 1];
    const current = points[index];
    const middle = (previous.x + current.x) / 2;
    chartContext.quadraticCurveTo(previous.x, previous.y, middle, (previous.y + current.y) / 2);
  }
  const last = points[points.length - 1];
  chartContext.lineTo(last.x, last.y);
  chartContext.strokeStyle = color;
  chartContext.lineWidth = 2.5;
  chartContext.lineCap = "round";
  chartContext.lineJoin = "round";
  chartContext.shadowColor = color;
  chartContext.shadowBlur = 9;
  chartContext.stroke();
  chartContext.shadowBlur = 0;

  for (const point of points) {
    chartContext.beginPath();
    chartContext.arc(point.x, point.y, 2.5, 0, Math.PI * 2);
    chartContext.fillStyle = color;
    chartContext.fill();
  }
}

function animateChart() {
  cancelAnimationFrame(chartFrame);
  let phase = 0;
  const animate = () => {
    if (dashboard.classList.contains("hidden")) return;
    phase += 0.04;
    chart.style.filter = `drop-shadow(0 0 ${2 + Math.sin(phase) * 2}px rgba(190, 125, 255, .18))`;
    chartFrame = requestAnimationFrame(animate);
  };
  chartFrame = requestAnimationFrame(animate);
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function setWidth(id, value) {
  document.getElementById(id).style.width = `${Math.max(0, Math.min(value, 100))}%`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function showError(message) {
  const toast = document.querySelector("#error-toast");
  toast.textContent = message;
  toast.className = `notice-toast ${message ? "warning" : "hidden"}`;
}

function showNotice(message, kind) {
  const toast = document.querySelector("#error-toast");
  toast.textContent = message;
  toast.className = `notice-toast ${kind}`;
}
