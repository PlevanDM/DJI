# Price Jump Monitor

This lightweight site visualizes price spikes and drops for your products so you
can react quickly to market moves. It highlights alerts directly on the chart
and summarizes key stats.

## Run locally

Serve the folder with any static server. For example:

```bash
cd price_insights
python3 -m http.server 8000
```

Open `http://localhost:8000` in your browser.

## Import your data

Use the **Add product data** section to upload a CSV or paste one in the text
area. The CSV must include these headers:

```
date,price
2026-01-01,419
2026-01-08,422
2026-01-15,398
```

## Alerts

- **Spike**: price increase that meets or exceeds the threshold.
- **Drop**: price decrease that meets or exceeds the threshold.

Adjust the threshold and moving average window to tune sensitivity.
