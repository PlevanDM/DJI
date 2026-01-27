const state = {
  products: [],
  chart: null
};

const fallbackProducts = [
  {
    name: "Power Station Delta 2",
    currency: "USD",
    series: [
      { date: "2025-11-25", price: 999 },
      { date: "2025-12-02", price: 979 },
      { date: "2025-12-09", price: 985 },
      { date: "2025-12-16", price: 912 },
      { date: "2025-12-23", price: 905 },
      { date: "2025-12-30", price: 948 },
      { date: "2026-01-06", price: 1025 },
      { date: "2026-01-13", price: 1012 },
      { date: "2026-01-20", price: 990 },
      { date: "2026-01-27", price: 1068 }
    ]
  },
  {
    name: "Compact Battery Pack",
    currency: "USD",
    series: [
      { date: "2025-11-25", price: 229 },
      { date: "2025-12-02", price: 225 },
      { date: "2025-12-09", price: 210 },
      { date: "2025-12-16", price: 215 },
      { date: "2025-12-23", price: 248 },
      { date: "2025-12-30", price: 252 },
      { date: "2026-01-06", price: 238 },
      { date: "2026-01-13", price: 241 },
      { date: "2026-01-20", price: 219 },
      { date: "2026-01-27", price: 224 }
    ]
  },
  {
    name: "Solar Panel 160W",
    currency: "USD",
    series: [
      { date: "2025-11-25", price: 349 },
      { date: "2025-12-02", price: 346 },
      { date: "2025-12-09", price: 332 },
      { date: "2025-12-16", price: 339 },
      { date: "2025-12-23", price: 318 },
      { date: "2025-12-30", price: 325 },
      { date: "2026-01-06", price: 352 },
      { date: "2026-01-13", price: 347 },
      { date: "2026-01-20", price: 361 },
      { date: "2026-01-27", price: 334 }
    ]
  }
];

const elements = {
  productSelect: document.getElementById("productSelect"),
  thresholdInput: document.getElementById("threshold"),
  maWindowInput: document.getElementById("maWindow"),
  refreshBtn: document.getElementById("refreshBtn"),
  alertList: document.getElementById("alertList"),
  summary: document.getElementById("summary"),
  chartCanvas: document.getElementById("priceChart"),
  importBtn: document.getElementById("importBtn"),
  csvFile: document.getElementById("csvFile"),
  csvSample: document.getElementById("csvSample"),
  newProductName: document.getElementById("newProductName"),
  importStatus: document.getElementById("importStatus")
};

function formatCurrency(value, currency) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "-";
  }
  const safeCurrency = currency || "USD";
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: safeCurrency,
      maximumFractionDigits: 2
    }).format(value);
  } catch (error) {
    const rounded = Math.round(value * 100) / 100;
    return `$${rounded.toFixed(2)}`;
  }
}

function formatPercent(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "-";
  }
  const rounded = Math.round(value * 10) / 10;
  return `${rounded.toFixed(1)}%`;
}

function parseCsv(text) {
  const trimmed = text.trim();
  if (!trimmed) {
    return [];
  }
  const lines = trimmed.split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) {
    return [];
  }
  const headers = lines[0].split(",").map((header) => header.trim().toLowerCase());
  const dateIndex = headers.indexOf("date");
  const priceIndex = headers.indexOf("price");
  if (dateIndex === -1 || priceIndex === -1) {
    return [];
  }

  const series = [];
  for (let i = 1; i < lines.length; i += 1) {
    const cells = lines[i].split(",").map((cell) => cell.trim());
    const date = cells[dateIndex];
    const priceValue = Number(cells[priceIndex]);
    if (!date || Number.isNaN(priceValue)) {
      continue;
    }
    series.push({ date, price: priceValue });
  }

  return series.sort((a, b) => new Date(a.date) - new Date(b.date));
}

function computeMovingAverage(series, windowSize) {
  const safeWindow = Math.max(2, Math.min(windowSize, series.length));
  return series.map((point, index) => {
    if (index < safeWindow - 1) {
      return null;
    }
    let sum = 0;
    for (let i = index - safeWindow + 1; i <= index; i += 1) {
      sum += series[i].price;
    }
    return Math.round((sum / safeWindow) * 100) / 100;
  });
}

function computeChanges(series, thresholdPct) {
  return series.map((point, index) => {
    if (index === 0) {
      return {
        ...point,
        change: 0,
        changePct: 0,
        type: "baseline"
      };
    }

    const previousPrice = series[index - 1].price;
    const change = point.price - previousPrice;
    const changePct = previousPrice === 0 ? 0 : (change / previousPrice) * 100;
    let type = "normal";
    if (changePct >= thresholdPct) {
      type = "spike";
    } else if (changePct <= -thresholdPct) {
      type = "drop";
    }

    return {
      ...point,
      change,
      changePct,
      type
    };
  });
}

function populateProducts() {
  elements.productSelect.innerHTML = "";
  state.products.forEach((product, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = product.name;
    elements.productSelect.appendChild(option);
  });
}

function renderAlerts(changes, currency) {
  const alerts = changes.filter((item) => item.type === "spike" || item.type === "drop");
  elements.alertList.innerHTML = "";

  if (alerts.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No alerts for the current threshold.";
    elements.alertList.appendChild(empty);
    return;
  }

  alerts.forEach((alert) => {
    const item = document.createElement("div");
    item.className = `alert-item ${alert.type}`;
    const title = document.createElement("h4");
    title.textContent = `${alert.type === "spike" ? "Spike" : "Drop"} on ${alert.date}`;
    const detail = document.createElement("p");
    detail.textContent = `${formatCurrency(alert.price, currency)} (${formatPercent(alert.changePct)})`;
    item.appendChild(title);
    item.appendChild(detail);
    elements.alertList.appendChild(item);
  });
}

function renderSummary(series, changes, currency) {
  if (series.length === 0) {
    elements.summary.textContent = "No data available.";
    return;
  }

  const prices = series.map((item) => item.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const avg = prices.reduce((sum, value) => sum + value, 0) / prices.length;
  const latest = series[series.length - 1];
  const latestChange = changes[changes.length - 1];
  const spikeCount = changes.filter((item) => item.type === "spike").length;
  const dropCount = changes.filter((item) => item.type === "drop").length;

  const rows = [
    ["Latest price", formatCurrency(latest.price, currency)],
    ["Latest change", formatPercent(latestChange.changePct)],
    ["Average price", formatCurrency(avg, currency)],
    ["Min price", formatCurrency(min, currency)],
    ["Max price", formatCurrency(max, currency)],
    ["Spike alerts", String(spikeCount)],
    ["Drop alerts", String(dropCount)]
  ];

  elements.summary.innerHTML = "";
  rows.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "summary-row";
    const labelEl = document.createElement("span");
    labelEl.textContent = label;
    const valueEl = document.createElement("strong");
    valueEl.textContent = value;
    row.appendChild(labelEl);
    row.appendChild(valueEl);
    elements.summary.appendChild(row);
  });
}

function renderChart(series, changes, movingAverage, currency) {
  const labels = series.map((item) => item.date);
  const prices = series.map((item) => item.price);
  const pointColors = changes.map((item) => {
    if (item.type === "spike") {
      return "#f97316";
    }
    if (item.type === "drop") {
      return "#0ea5e9";
    }
    return "#64748b";
  });
  const pointRadius = changes.map((item) => (item.type === "spike" || item.type === "drop" ? 6 : 3));

  const data = {
    labels,
    datasets: [
      {
        label: "Price",
        data: prices,
        borderColor: "#334155",
        backgroundColor: "rgba(51, 65, 85, 0.1)",
        pointBackgroundColor: pointColors,
        pointRadius,
        tension: 0.25,
        fill: true
      },
      {
        label: "Moving average",
        data: movingAverage,
        borderColor: "#16a34a",
        borderDash: [6, 4],
        pointRadius: 0,
        spanGaps: false
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: "index",
      intersect: false
    },
    plugins: {
      legend: {
        position: "top"
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            if (context.dataset.label === "Price") {
              return `${context.dataset.label}: ${formatCurrency(context.parsed.y, currency)}`;
            }
            return `${context.dataset.label}: ${formatCurrency(context.parsed.y, currency)}`;
          }
        }
      }
    },
    scales: {
      y: {
        ticks: {
          callback: (value) => formatCurrency(value, currency)
        }
      }
    }
  };

  if (!state.chart) {
    state.chart = new Chart(elements.chartCanvas, {
      type: "line",
      data,
      options
    });
    return;
  }

  state.chart.data = data;
  state.chart.options = options;
  state.chart.update();
}

function render() {
  const selectedIndex = Number(elements.productSelect.value) || 0;
  const product = state.products[selectedIndex];
  if (!product) {
    return;
  }
  const thresholdPct = Number(elements.thresholdInput.value) || 0;
  const maWindow = Number(elements.maWindowInput.value) || 3;
  const series = [...product.series].sort((a, b) => new Date(a.date) - new Date(b.date));
  const changes = computeChanges(series, thresholdPct);
  const movingAverage = computeMovingAverage(series, maWindow);

  renderAlerts(changes, product.currency);
  renderSummary(series, changes, product.currency);
  renderChart(series, changes, movingAverage, product.currency);
}

function setImportStatus(message, isError) {
  elements.importStatus.textContent = message;
  elements.importStatus.classList.toggle("error", Boolean(isError));
}

async function handleImport() {
  const name = elements.newProductName.value.trim();
  if (!name) {
    setImportStatus("Please provide a product name.", true);
    return;
  }

  let csvText = "";
  if (elements.csvFile.files.length > 0) {
    const file = elements.csvFile.files[0];
    csvText = await file.text();
  } else {
    csvText = elements.csvSample.value;
  }

  const series = parseCsv(csvText);
  if (series.length < 2) {
    setImportStatus("Could not parse CSV. Make sure it has date,price columns.", true);
    return;
  }

  state.products.push({
    name,
    currency: "USD",
    series
  });
  populateProducts();
  elements.productSelect.value = String(state.products.length - 1);
  setImportStatus("Product imported successfully.", false);
  render();
}

async function init() {
  try {
    const response = await fetch("data.json");
    const payload = await response.json();
    state.products = payload.products || [];
  } catch (error) {
    state.products = [];
  }
  if (state.products.length === 0) {
    state.products = fallbackProducts;
  }
  populateProducts();
  render();
}

elements.productSelect.addEventListener("change", render);
elements.refreshBtn.addEventListener("click", render);
elements.thresholdInput.addEventListener("change", render);
elements.maWindowInput.addEventListener("change", render);
elements.importBtn.addEventListener("click", () => {
  handleImport();
});

init();
