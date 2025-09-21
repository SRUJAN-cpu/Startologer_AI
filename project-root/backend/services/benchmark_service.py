import csv
import os
from typing import Dict, Any
from datetime import datetime
from urllib.parse import urlparse

try:
    import requests  # used only if BENCHMARK_CSV_URL is set
except Exception:
    requests = None  # type: ignore

HERE = os.path.dirname(__file__)
CSV_PATH = os.path.join(os.path.dirname(HERE), 'models', 'benchmarks.csv')

_ROWS: list[Dict[str, str]] = []
_SOURCE_INFO: Dict[str, Any] = {"source": "local", "path": CSV_PATH, "rows": 0, "loadedAt": None}


def _load_from_local(path: str) -> list[Dict[str, str]]:
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _load_from_url(url: str) -> list[Dict[str, str]]:
    if not requests:
        return []
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    text = resp.text
    # Handle potential UTF-8 BOM
    if text and text[0] == '\ufeff':
        text = text[1:]
    reader = csv.DictReader(text.splitlines())
    return list(reader)


def reload_benchmarks() -> Dict[str, Any]:
    """Reload the benchmarks into memory from URL or local file.
    Env var: BENCHMARK_CSV_URL (optional). Fallback to local CSV_PATH.
    """
    global _ROWS, _SOURCE_INFO
    url = os.getenv('BENCHMARK_CSV_URL', '').strip()
    rows: list[Dict[str, str]] = []
    src: Dict[str, Any] = {}
    try:
        if url:
            rows = _load_from_url(url)
            src = {
                "source": "url",
                "url": url,
                "rows": len(rows),
            }
        if not rows:
            rows = _load_from_local(CSV_PATH)
            src = {
                "source": "local",
                "path": CSV_PATH,
                "rows": len(rows),
            }
    except Exception as e:
        # On error, keep previous data
        src = {"source": "error", "error": str(e), "rows": len(_ROWS)}

    _ROWS = rows or _ROWS
    _SOURCE_INFO = {
        **src,
        "loadedAt": datetime.utcnow().isoformat() + "Z",
    }
    return {"ok": True, **_SOURCE_INFO}


# Initial load
reload_benchmarks()

def _find_row(sector: str, stage: str, metric: str):
    for r in _ROWS:
        if r['sector'] == sector and r['stage'] == stage and r['metric'] == metric:
            return r
    return None

def benchmark_metrics(metrics: Dict[str, Any], sector: str | None, stage: str | None) -> Dict[str, Any]:
    """Return benchmark comparison for available metrics using a local CSV.
    Output per metric: companyValue, median, p25, p75, percentile (rough), status.
    """
    out: Dict[str, Any] = {}
    if not sector or not stage:
        return out

    def compute(name: str, higher_is_better: bool = True):
        val = metrics.get(name)
        if val is None:
            return
        row = _find_row(sector, stage, name)
        if not row:
            return
        median = float(row['median'])
        p25 = float(row['p25'])
        p75 = float(row['p75'])
        # crude percentile estimate within IQR
        if val <= p25:
            perc = 0.1
        elif val >= p75:
            perc = 0.9
        else:
            perc = 0.1 + 0.8 * ((val - p25) / (p75 - p25))
        status = 'above' if (higher_is_better and val >= median) or (not higher_is_better and val <= median) else 'below'
        out[name] = {
            'companyValue': val,
            'median': median,
            'p25': p25,
            'p75': p75,
            'percentile': perc,
            'status': status
        }

    # Growth, margins, LTV are higher-is-better; churn, CAC are lower-is-better
    compute('arr', True)
    compute('mrr', True)
    compute('growthYoY', True)
    compute('growthMoM', True)
    compute('grossMargin', True)
    compute('ltv', True)
    compute('headcount', True)
    compute('runwayMonths', True)
    compute('churnRate', False)
    compute('cac', False)

    return out

def score_from_benchmarks(bench: Dict[str, Any], weights: Dict[str, float] | None = None) -> Dict[str, Any]:
    """Compute a composite score from metric percentiles and weights."""
    if not bench:
        return {'composite': None, 'weights': {}, 'metricScores': {}}
    default_weights = {
        'growthYoY': 0.25,
        'churnRate': 0.2,
        'grossMargin': 0.15,
        'cac': 0.15,
        'ltv': 0.15,
        'runwayMonths': 0.1,
      }
    w = weights or default_weights
    # normalize
    total = sum(w.values()) or 1.0
    w = {k: v / total for k, v in w.items()}
    metric_scores: Dict[str, float] = {}
    composite = 0.0
    for k, weight in w.items():
        perc = bench.get(k, {}).get('percentile')
        if perc is None:
            continue
        metric_scores[k] = perc
        composite += perc * weight
    verdict = 'Proceed' if composite >= 0.7 else ('Track' if composite >= 0.5 else 'Pass')
    return {'composite': composite, 'verdict': verdict, 'weights': w, 'metricScores': metric_scores}


def get_benchmark_source_info() -> Dict[str, Any]:
    return {**_SOURCE_INFO}
