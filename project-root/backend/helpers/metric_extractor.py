import re
from typing import Dict, Optional

MULTIPLIERS = {
    'k': 1_000,
    'm': 1_000_000,
    'mn': 1_000_000,
    'million': 1_000_000,
    'b': 1_000_000_000,
    'bn': 1_000_000_000,
    'billion': 1_000_000_000,
    'cr': 10_000_000,  # Crore
    'crore': 10_000_000,
    'l': 100_000,      # Lakh
    'lakh': 100_000,
}

def _to_number(val: str) -> Optional[float]:
    if not val:
        return None
    s = val.strip().lower()
    s = s.replace(',', '').replace('₹', '').replace('inr', '').strip()
    m = re.match(r"([0-9]*\.?[0-9]+)\s*([a-z]+)?", s)
    if not m:
        try:
            return float(s)
        except Exception:
            return None
    num = float(m.group(1))
    unit = m.group(2) or ''
    mul = MULTIPLIERS.get(unit, 1)
    return num * mul

def extract_metrics(text: str) -> Dict[str, Optional[float]]:
    """Very lightweight regex-based extractor for common metrics.
    Returns numbers when found; otherwise None.
    """
    out: Dict[str, Optional[float]] = {
        'arr': None,
        'mrr': None,
        'cac': None,
        'ltv': None,
        'churnRate': None,
        'growthYoY': None,
        'growthMoM': None,
        'headcount': None,
        'runwayMonths': None,
        'grossMargin': None,
        'sector': None,
        'stage': None,
    }
    if not text:
        return out

    # Normalize
    t = text.lower()

    # ARR / MRR
    m = re.search(r"arr\s*[:=]?\s*([\w\.,]+)\s*(cr|crore|mn|m|k|b|bn|million|billion)?", t)
    if m:
        out['arr'] = _to_number((m.group(1) + ' ' + (m.group(2) or '')).strip())
    m = re.search(r"mrr\s*[:=]?\s*([\w\.,]+)\s*(cr|crore|mn|m|k|b|bn|million|billion)?", t)
    if m:
        out['mrr'] = _to_number((m.group(1) + ' ' + (m.group(2) or '')).strip())

    # CAC / LTV (look for currency or numbers)
    m = re.search(r"cac\s*[:=]?\s*([₹$]?[\w\.,]+)\s*(cr|crore|mn|m|k|b|bn|million|billion)?", t)
    if m:
        out['cac'] = _to_number((m.group(1) + ' ' + (m.group(2) or '')).strip())
    m = re.search(r"ltv\s*[:=]?\s*([₹$]?[\w\.,]+)\s*(cr|crore|mn|m|k|b|bn|million|billion)?", t)
    if m:
        out['ltv'] = _to_number((m.group(1) + ' ' + (m.group(2) or '')).strip())

    # Churn %, Growth %, GM %, Runway months
    m = re.search(r"churn[^\d%]*([\d]{1,2}(?:\.\d+)?)\s*%", t)
    if m:
        out['churnRate'] = float(m.group(1)) / 100.0
    m = re.search(r"growth[^\d%]*([\-\d]{1,3}(?:\.\d+)?)\s*%\s*yo?y", t)
    if m:
        out['growthYoY'] = float(m.group(1)) / 100.0
    m = re.search(r"growth[^\d%]*([\-\d]{1,3}(?:\.\d+)?)\s*%\s*mom", t)
    if m:
        out['growthMoM'] = float(m.group(1)) / 100.0
    m = re.search(r"gross\s*margin[^\d%]*([\d]{1,3}(?:\.\d+)?)\s*%", t)
    if m:
        out['grossMargin'] = float(m.group(1)) / 100.0
    m = re.search(r"runway[^\d]*([\d]{1,3})\s*(?:months|mos|m)\b", t)
    if m:
        out['runwayMonths'] = float(m.group(1))

    # Headcount
    m = re.search(r"headcount[^\d]*([\d]{1,5})\b", t)
    if m:
        out['headcount'] = float(m.group(1))
    m = re.search(r"team\s*size[^\d]*([\d]{1,5})\b", t)
    if m and not out['headcount']:
        out['headcount'] = float(m.group(1))

    # Sector / Stage (very naive)
    m = re.search(r"sector\s*[:=]?\s*([\w\-\s]+)\b", t)
    if m:
        out['sector'] = m.group(1).strip()[:50]
    m = re.search(r"stage\s*[:=]?\s*(pre-seed|seed|series\s*a|series\s*b|growth|late)\b", t)
    if m:
        out['stage'] = m.group(1).strip()

    return out
