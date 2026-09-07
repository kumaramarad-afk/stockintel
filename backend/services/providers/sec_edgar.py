from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from services.cache import cached
from services.keys import sec_user_agent
from services.numbers import iso, to_float

logger = logging.getLogger(__name__)

FORM4_CODES = {
    "P": "Acquired",
    "S": "Disposed",
    "A": "Award",
    "M": "Exercise",
    "G": "Gift",
    "F": "Tax withholding",
    "D": "Disposition",
    "C": "Conversion",
}

MAJOR_13F_CIKS = [
    ("0000102909", "Vanguard Group"),
    ("0001364742", "BlackRock"),
    ("0001086364", "BlackRock Institutional Trust"),
    ("0000315066", "FMR LLC"),
    ("0000093751", "State Street"),
    ("0001424472", "Geode Capital"),
    ("0001067983", "Berkshire Hathaway"),
    ("0000104169", "JPMorgan Chase"),
    ("0000869102", "T. Rowe Price"),
    ("0000103123", "Morgan Stanley"),
    ("0000807249", "Dimensional Fund Advisors"),
    ("0000949509", "Invesco"),
]


def _client() -> httpx.Client:
    return httpx.Client(
        timeout=25.0,
        headers={"User-Agent": sec_user_agent() or "StockIntel research@example.com", "Accept-Encoding": "gzip"},
        follow_redirects=True,
    )


def _local(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _find_text(node: ET.Element | None, *names: str) -> str | None:
    if node is None:
        return None
    if not names:
        value_el = next((child for child in list(node) if _local(child.tag) == "value"), None)
        if value_el is not None and value_el.text:
            return value_el.text.strip()
        return (node.text or "").strip() or None
    name = names[0]
    for child in node:
        if _local(child.tag) == name:
            return _find_text(child, *names[1:])
    for child in node.iter():
        if _local(child.tag) == name:
            return _find_text(child, *names[1:])
    return None


KNOWN_CUSIPS = {
    "AAPL": "037833100",
    "MSFT": "594918104",
    "GOOGL": "02079K305",
    "GOOG": "02079K107",
    "AMZN": "023135106",
    "NVDA": "67066G104",
    "META": "30303M102",
    "TSLA": "88160R101",
    "JPM": "46625H100",
    "BRK.B": "084670702",
    "BRK-B": "084670702",
}


def _cik_map() -> dict[str, dict[str, str]]:
    def _fetch() -> dict[str, dict[str, str]]:
        mapping: dict[str, dict[str, str]] = {}
        try:
            with _client() as client:
                response = client.get("https://www.sec.gov/files/company_tickers.json")
                response.raise_for_status()
                payload = response.json()
            for item in payload.values() if isinstance(payload, dict) else []:
                ticker = str(item.get("ticker") or "").upper()
                cik = str(item.get("cik_str") or "").zfill(10)
                title = str(item.get("title") or "")
                if ticker:
                    mapping[ticker] = {"cik": cik, "title": title}
        except Exception:
            logger.exception("SEC ticker map failed")
        return mapping

    return cached("sec:tickers", _fetch, ttl=86400)


def cik_for(ticker: str) -> str | None:
    row = _cik_map().get(ticker.upper().replace("-", ".")) or _cik_map().get(ticker.upper()) or _cik_map().get(ticker.upper().replace(".", "-"))
    return (row or {}).get("cik")


def issuer_title(ticker: str) -> str | None:
    row = _cik_map().get(ticker.upper().replace("-", ".")) or _cik_map().get(ticker.upper())
    return (row or {}).get("title")


def _submissions(cik: str) -> dict[str, Any] | None:
    padded = cik.zfill(10)

    def _fetch() -> dict[str, Any] | None:
        try:
            with _client() as client:
                response = client.get(f"https://data.sec.gov/submissions/CIK{padded}.json")
                if response.status_code >= 400:
                    return None
                payload = response.json()
            return payload if isinstance(payload, dict) else None
        except Exception:
            logger.exception("SEC submissions failed for %s", cik)
            return None

    return cached(f"sec:sub:{padded}", _fetch, ttl=1800)


def _filing_files(cik: str, accession: str) -> list[str]:
    cik_num = str(int(cik))
    accdir = accession.replace("-", "")
    try:
        with _client() as client:
            response = client.get(f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{accdir}/index.json")
            if response.status_code >= 400:
                return []
            items = ((response.json().get("directory") or {}).get("item") or [])
        return [str(item.get("name")) for item in items if item.get("name")]
    except Exception:
        logger.debug("SEC index.json failed for %s %s", cik, accession, exc_info=True)
        return []


def _filing_text(cik: str, accession: str, name: str) -> str | None:
    cik_num = str(int(cik))
    accdir = accession.replace("-", "")
    try:
        with _client() as client:
            response = client.get(f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{accdir}/{name}")
            if response.status_code >= 400:
                return None
            return response.text
    except Exception:
        logger.debug("SEC filing fetch failed %s", name, exc_info=True)
        return None


def insider_transactions(ticker: str) -> list[dict[str, Any]]:
    cik = cik_for(ticker)
    if not cik:
        return []

    def _fetch() -> list[dict[str, Any]]:
        payload = _submissions(cik)
        recent = ((payload or {}).get("filings") or {}).get("recent") or {}
        forms = recent.get("form") or []
        accessions = recent.get("accessionNumber") or []
        dates = recent.get("filingDate") or []
        cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).date()
        items: list[dict[str, Any]] = []
        seen = 0
        for form, accession, filed in zip(forms, accessions, dates):
            if str(form).strip() != "4":
                continue
            try:
                filed_date = datetime.fromisoformat(str(filed)).date()
            except Exception:
                filed_date = None
            if filed_date and filed_date < cutoff:
                continue
            files = _filing_files(cik, accession)
            xml_name = next((name for name in files if name.lower() == "form4.xml"), None)
            xml_name = xml_name or next((name for name in files if name.lower().endswith(".xml") and "xsl" not in name.lower()), None)
            if not xml_name:
                continue
            text = _filing_text(cik, accession, xml_name)
            if not text:
                continue
            items.extend(_parse_form4(text, filed))
            seen += 1
            if seen >= 12 or len(items) >= 20:
                break
        return items[:20]

    return cached(f"sec:form4:{cik}", _fetch, ttl=1800)


def _parse_form4(xml_text: str, filing_date: str | None) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    name = _find_text(root, "rptOwnerName")
    title = _find_text(root, "officerTitle") or _find_text(root, "otherText")
    rows: list[dict[str, Any]] = []
    for node in root.iter():
        if _local(node.tag) not in {"nonDerivativeTransaction", "derivativeTransaction"}:
            continue
        code = (_find_text(node, "transactionCode") or "").upper()
        shares = to_float(_find_text(node, "transactionShares"))
        price = to_float(_find_text(node, "transactionPricePerShare"))
        when = _find_text(node, "transactionDate") or filing_date
        action = FORM4_CODES.get(code, code or "Form 4")
        value = shares * price if shares is not None and price is not None else None
        if shares is None and value is None:
            continue
        rows.append(
            {
                "name": name,
                "title": title,
                "action": action,
                "shares": shares,
                "value": value,
                "date": iso(when),
                "source": "sec",
                "code": code,
            }
        )
    return rows


def thirteen_f_holdings(ticker: str, issuer_name: str | None = None) -> dict[str, Any]:
    needle = _norm(issuer_name or issuer_title(ticker) or ticker)
    cusip_want = KNOWN_CUSIPS.get(ticker.upper()) or KNOWN_CUSIPS.get(ticker.upper().replace(".", "-"))

    def _one(cik: str, holder_name: str) -> dict[str, Any] | None:
        filing = _latest_13f_hr(cik)
        if not filing:
            return None
        files = _filing_files(cik, filing["accession"])
        table_name = next((name for name in files if name.lower().startswith("13f_") and name.lower().endswith(".xml")), None)
        table_name = table_name or next((name for name in files if "infotable" in name.lower()), None)
        if not table_name:
            return None
        text = _filing_text(cik, filing["accession"], table_name)
        if not text:
            return None
        row = _parse_13f_row(text, ticker, needle, cusip_want)
        if not row:
            return None
        row["holder"] = holder_name
        row["report_date"] = filing.get("date")
        return row

    def _fetch() -> dict[str, Any]:
        holders: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(_one, cik, name) for cik, name in MAJOR_13F_CIKS]
            for future in as_completed(futures):
                try:
                    row = future.result()
                except Exception:
                    logger.debug("13F holder fetch failed", exc_info=True)
                    continue
                if row:
                    holders.append(row)
        holders.sort(key=lambda item: item.get("value") or 0, reverse=True)
        return {
            "top_holders": holders[:8],
            "holder_count": len(holders),
            "latest_13f": holders[0]["report_date"] if holders else None,
        }

    return cached(f"sec:13fhold:{ticker}:{needle}:{cusip_want}", _fetch, ttl=21600)


def _latest_13f_hr(cik: str) -> dict[str, str] | None:
    payload = _submissions(cik)
    recent = ((payload or {}).get("filings") or {}).get("recent") or {}
    for form, accession, filed in zip(recent.get("form") or [], recent.get("accessionNumber") or [], recent.get("filingDate") or []):
        label = str(form).upper()
        if label.startswith("13F-HR") and "NT" not in label:
            return {"accession": accession, "date": filed, "form": form}
    return None


def _parse_13f_row(xml_text: str, ticker: str, issuer_norm: str, cusip_want: str | None) -> dict[str, Any] | None:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None
    ticker_u = ticker.upper()
    best: dict[str, Any] | None = None
    for node in root.iter():
        if _local(node.tag) not in {"infoTable", "infotable"}:
            continue
        issuer = _find_text(node, "nameOfIssuer") or ""
        title = _find_text(node, "titleOfClass") or ""
        cusip = (_find_text(node, "cusip") or "").upper().replace(" ", "")
        n_issuer = _norm(issuer)
        matched = False
        if cusip_want and cusip.startswith(cusip_want[:8]):
            matched = True
        elif issuer_norm and len(issuer_norm) >= 5 and issuer_norm[:8] in n_issuer:
            matched = True
        elif ticker_u in f"{issuer} {title}".upper().split():
            matched = True
        if not matched:
            continue
        shares = to_float(_find_text(node, "sshPrnamt"))
        value = to_float(_find_text(node, "value"))
        if value is not None and value < 10_000_000:
            value *= 1000
        row = {"shares": shares, "value": value, "cusip": cusip, "issuer": issuer, "pct": None, "change": None}
        if best is None or (value or 0) > (best.get("value") or 0):
            best = row
    return best


def _norm(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def thirteen_f_summary(ticker: str) -> dict[str, Any] | None:
    holdings = thirteen_f_holdings(ticker)
    if not holdings.get("top_holders"):
        return None
    return holdings
