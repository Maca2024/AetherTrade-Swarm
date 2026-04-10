"""
AETHERTRADE-SWARM — SEC EDGAR Form 4 Insider Trade Fetcher

Fetches, parses, and stores Form 4 filings from SEC EDGAR.
Form 4 is XML-structured and contains all insider transaction details.

SEC Fair Use: max 10 requests/second, required User-Agent header.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any
from xml.etree import ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("aethertrade.insider.edgar_fetcher")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEC_BASE = "https://www.sec.gov"
# Current Form 4 filings feed (most recent 40)
CURRENT_FEED_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar"
    "?action=getcurrent&type=4&dateb=&owner=include&count=40&output=atom"
)
# Company-specific browse URL template
COMPANY_FEED_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar"
    "?action=getcompany&type=4&dateb=&owner=include&count=40&output=atom&CIK={cik}"
)
ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"

# SEC requires a descriptive User-Agent — violations result in IP bans.
USER_AGENT = "AetherTrade Research research@aetherlink.ai"

# Delay between SEC requests to stay within fair-use rate limits
SEC_REQUEST_DELAY_SEC = 0.12  # ~8 req/s (under the 10/s limit)

# Transaction codes that represent open-market activity
TRANSACTION_CODE_LABELS: dict[str, str] = {
    "P": "Open Market Purchase",
    "S": "Open Market Sale",
    "A": "Grant/Award",
    "D": "Return/Disposition",
    "F": "Tax Withholding",
    "G": "Gift",
    "M": "Option Exercise",
    "C": "Conversion",
    "E": "Expiration of Short",
    "H": "Expiration of Long",
    "I": "Discretionary Transaction",
    "J": "Other Acquisition/Disposition",
    "K": "Equity Swap",
    "L": "Small Acquisition",
    "O": "Option Exercise (out of the money)",
    "U": "Fund Tender Offer",
    "W": "Inheritance/Will",
    "X": "Option Exercise (in the money)",
    "Z": "Voting Trust",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class InsiderTrade:
    """Parsed Form 4 transaction record."""

    # Company identifiers
    cik: str
    ticker: str
    company_name: str

    # Insider
    insider_name: str
    insider_title: str

    # Transaction
    transaction_date: date
    transaction_code: str
    shares: float
    price_per_share: float
    total_value: float
    shares_owned_after: float

    # Filing metadata
    filing_timestamp: datetime
    form4_url: str

    # Internal (set after DB insert)
    id: str | None = None


@dataclass
class FilingRef:
    """Lightweight reference extracted from EDGAR Atom feed."""

    accession: str          # e.g. 0001234567-24-000001
    filing_url: str         # https://www.sec.gov/Archives/...
    index_url: str          # .../index.json
    filed_at: datetime
    cik: str
    issuer_ticker: str
    issuer_name: str


# ---------------------------------------------------------------------------
# HTTP session with retry logic
# ---------------------------------------------------------------------------

def _build_session() -> requests.Session:
    """
    Build a requests.Session with:
    - Retry on 429, 500, 502, 503, 504 (backoff factor 1 sec)
    - Required SEC User-Agent header
    - 30-second timeout default
    """
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist={429, 500, 502, 503, 504},
        allowed_methods={"GET"},
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Accept": "application/json, application/xml, text/html, */*",
    })
    return session


_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = _build_session()
    return _session


def _sec_get(url: str, timeout: int = 30) -> requests.Response:
    """
    Rate-limited GET against SEC EDGAR.
    Enforces the SEC inter-request delay to avoid 429s.
    """
    time.sleep(SEC_REQUEST_DELAY_SEC)
    resp = _get_session().get(url, timeout=timeout)
    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------------------
# Feed parsing — Atom XML
# ---------------------------------------------------------------------------

def _parse_atom_feed(xml_text: str) -> list[dict[str, Any]]:
    """
    Parse EDGAR Atom feed XML. Returns list of entry dicts with
    keys: accession, filing_url, filed_at, cik, issuer_ticker, issuer_name.
    """
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml_text)
    entries: list[dict[str, Any]] = []

    for entry in root.findall("atom:entry", ns):
        try:
            link_el = entry.find("atom:link", ns)
            filing_url = link_el.attrib.get("href", "") if link_el is not None else ""

            updated_el = entry.find("atom:updated", ns)
            filed_at_str = updated_el.text if updated_el is not None else ""
            try:
                filed_at = datetime.fromisoformat(
                    filed_at_str.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                filed_at = datetime.now(timezone.utc)

            # Entry id format: urn:tag:www.sec.gov,...:<cik>/<accession>
            id_el = entry.find("atom:id", ns)
            entry_id = id_el.text if id_el is not None else ""
            cik = ""
            if entry_id and "/" in entry_id:
                parts = entry_id.rsplit("/", 2)
                if len(parts) >= 2:
                    cik = parts[-2].lstrip("0")

            # Category contains company name + ticker
            category_el = entry.find("atom:category", ns)
            issuer_name = ""
            issuer_ticker = ""
            if category_el is not None:
                label = category_el.attrib.get("label", "")
                # Label format: "Company Name (TICKER)"
                if "(" in label and label.endswith(")"):
                    issuer_ticker = label.rsplit("(", 1)[-1].rstrip(")")
                    issuer_name = label.rsplit("(", 1)[0].strip()
                else:
                    issuer_name = label

            entries.append({
                "filing_url": filing_url,
                "filed_at": filed_at,
                "cik": cik,
                "issuer_ticker": issuer_ticker,
                "issuer_name": issuer_name,
            })

        except Exception as exc:
            logger.debug("Skipping malformed feed entry: %s", exc)

    return entries


# ---------------------------------------------------------------------------
# Form 4 XML parsing
# ---------------------------------------------------------------------------

def _safe_text(el: ET.Element | None, default: str = "") -> str:
    if el is None or el.text is None:
        return default
    return el.text.strip()


def _safe_float(el: ET.Element | None, default: float = 0.0) -> float:
    text = _safe_text(el)
    if not text:
        return default
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return default


def _find_form4_xml_url(index_url: str) -> str | None:
    """
    Fetch the filing index and locate the primary Form 4 XML document URL.
    SEC filing indexes are available as JSON at /Archives/edgar/data/{cik}/{accession}/index.json
    """
    try:
        resp = _sec_get(index_url)
        data = resp.json()
        documents = data.get("directory", {}).get("item", [])
        # Prefer .xml files that are not the index itself
        for doc in documents:
            name = doc.get("name", "")
            if name.endswith(".xml") and "index" not in name.lower():
                base = index_url.rsplit("/", 1)[0]
                return f"{base}/{name}"
    except Exception as exc:
        logger.debug("Could not parse filing index %s: %s", index_url, exc)
    return None


def _filing_url_to_index_json(filing_url: str) -> str:
    """
    Convert an EDGAR filing page URL to the index.json URL.
    e.g. /Archives/edgar/data/12345/000123456724000001/0001234567-24-000001-index.htm
      -> /Archives/edgar/data/12345/000123456724000001/index.json
    """
    # Normalise to base directory
    if "/" in filing_url:
        base = filing_url.rsplit("/", 1)[0]
    else:
        base = filing_url
    if not base.startswith("http"):
        base = SEC_BASE + base
    return base.rstrip("/") + "/index.json"


def parse_form4_xml(xml_text: str, cik: str, ticker: str, company_name: str,
                    filing_url: str, filed_at: datetime) -> list[InsiderTrade]:
    """
    Parse a Form 4 XML document into a list of InsiderTrade records.
    One Form 4 may contain multiple non-derivative or derivative transactions.

    Returns empty list if the XML is not parseable or contains no P/S transactions.
    """
    trades: list[InsiderTrade] = []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("Form 4 XML parse error for CIK %s: %s", cik, exc)
        return trades

    # --- Issuer info (may override feed data) ---
    issuer_el = root.find(".//issuer")
    if issuer_el is not None:
        cik_from_xml = _safe_text(issuer_el.find("issuerCik"), cik).lstrip("0")
        cik = cik_from_xml or cik
        company_name = _safe_text(issuer_el.find("issuerName"), company_name)
        ticker = _safe_text(issuer_el.find("issuerTradingSymbol"), ticker)

    # --- Reporting owner (insider) info ---
    owner_name = ""
    owner_title = ""

    owner_el = root.find(".//reportingOwner")
    if owner_el is not None:
        owner_id = owner_el.find("reportingOwnerId")
        if owner_id is not None:
            owner_name = _safe_text(owner_id.find("rptOwnerName"))

        owner_rel = owner_el.find("reportingOwnerRelationship")
        if owner_rel is not None:
            titles: list[str] = []
            if _safe_text(owner_rel.find("isOfficer")) == "1":
                titles.append(_safe_text(owner_rel.find("officerTitle"), "Officer"))
            if _safe_text(owner_rel.find("isDirector")) == "1":
                titles.append("Director")
            if _safe_text(owner_rel.find("isTenPercentOwner")) == "1":
                titles.append("10% Owner")
            if _safe_text(owner_rel.find("isOther")) == "1":
                other_text = _safe_text(owner_rel.find("otherText"))
                titles.append(other_text or "Other")
            owner_title = ", ".join(titles) if titles else "Insider"

    # Guard: skip 10% holders (passive institutional) — they are not
    # executive insiders and distort cluster signals.
    if "10% Owner" in owner_title and "Director" not in owner_title and "Officer" not in owner_title:
        logger.debug("Skipping 10%% holder %s at %s", owner_name, company_name)
        return trades

    # --- Non-derivative transactions ---
    for txn in root.findall(".//nonDerivativeTransaction"):
        trade = _parse_transaction_element(
            txn=txn,
            cik=cik,
            ticker=ticker,
            company_name=company_name,
            insider_name=owner_name,
            insider_title=owner_title,
            filing_url=filing_url,
            filed_at=filed_at,
        )
        if trade is not None:
            trades.append(trade)

    return trades


def _parse_transaction_element(
    txn: ET.Element,
    cik: str,
    ticker: str,
    company_name: str,
    insider_name: str,
    insider_title: str,
    filing_url: str,
    filed_at: datetime,
) -> InsiderTrade | None:
    """
    Parse a single <nonDerivativeTransaction> element into an InsiderTrade.
    Returns None if the element is missing required fields.
    """
    code_el = txn.find(".//transactionCode")
    transaction_code = _safe_text(code_el)
    if not transaction_code:
        return None

    date_el = txn.find(".//transactionDate/value")
    date_str = _safe_text(date_el)
    try:
        transaction_date = date.fromisoformat(date_str)
    except ValueError:
        logger.debug("Bad transaction date '%s' — skipping", date_str)
        return None

    shares = _safe_float(txn.find(".//transactionShares/value"))
    price_per_share = _safe_float(txn.find(".//transactionPricePerShare/value"))

    # Determine sign from acquired/disposed indicator
    acq_disp = _safe_text(txn.find(".//transactionAcquiredDisposedCode/value"))
    if acq_disp == "D":
        shares = -abs(shares)  # disposition = negative
    else:
        shares = abs(shares)   # acquisition = positive

    total_value = abs(shares) * price_per_share

    shares_owned_after = _safe_float(
        txn.find(".//sharesOwnedFollowingTransaction/value")
    )

    return InsiderTrade(
        cik=cik,
        ticker=ticker.upper(),
        company_name=company_name,
        insider_name=insider_name,
        insider_title=insider_title,
        transaction_date=transaction_date,
        transaction_code=transaction_code,
        shares=shares,
        price_per_share=price_per_share,
        total_value=total_value,
        shares_owned_after=shares_owned_after,
        filing_timestamp=filed_at,
        form4_url=filing_url,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_recent_form4s(count: int = 40) -> list[InsiderTrade]:
    """
    Fetch the most recent Form 4 filings from the EDGAR current-feed endpoint.
    Parses each XML and returns a flat list of InsiderTrade records.

    Args:
        count: Number of filings to attempt (feed returns up to 40 per page)

    Returns:
        List of parsed InsiderTrade records (may be empty on network errors)
    """
    logger.info("Fetching recent Form 4 feed (count=%d)", count)
    all_trades: list[InsiderTrade] = []

    try:
        resp = _sec_get(CURRENT_FEED_URL)
        entries = _parse_atom_feed(resp.text)
    except Exception as exc:
        logger.error("Failed to fetch EDGAR current feed: %s", exc)
        return all_trades

    logger.info("Feed returned %d entries, fetching Form 4 XML for each", len(entries))

    for entry in entries[:count]:
        try:
            trades = _fetch_and_parse_single_filing(entry)
            all_trades.extend(trades)
        except Exception as exc:
            logger.warning("Error processing filing %s: %s", entry.get("filing_url", "?"), exc)

    logger.info("Parsed %d insider trade records from %d filings", len(all_trades), len(entries))
    return all_trades


def fetch_form4s_for_company(cik: str) -> list[InsiderTrade]:
    """
    Fetch the most recent 40 Form 4 filings for a specific company by CIK.

    Args:
        cik: SEC Central Index Key (numeric string, leading zeros stripped)

    Returns:
        List of InsiderTrade records for that company
    """
    logger.info("Fetching Form 4 filings for CIK %s", cik)
    all_trades: list[InsiderTrade] = []

    url = COMPANY_FEED_URL.format(cik=cik)
    try:
        resp = _sec_get(url)
        entries = _parse_atom_feed(resp.text)
    except Exception as exc:
        logger.error("Failed to fetch company feed for CIK %s: %s", cik, exc)
        return all_trades

    for entry in entries:
        try:
            trades = _fetch_and_parse_single_filing(entry)
            all_trades.extend(trades)
        except Exception as exc:
            logger.warning("Error processing company filing: %s", exc)

    return all_trades


def _fetch_and_parse_single_filing(entry: dict[str, Any]) -> list[InsiderTrade]:
    """
    Given a feed entry dict, fetch the actual Form 4 XML and parse it.
    """
    filing_url = entry.get("filing_url", "")
    cik = entry.get("cik", "")
    ticker = entry.get("issuer_ticker", "")
    company_name = entry.get("issuer_name", "")
    filed_at = entry.get("filed_at", datetime.now(timezone.utc))

    if not filing_url:
        return []

    # Build index.json URL from the filing page URL
    index_json_url = _filing_url_to_index_json(filing_url)

    # Find the primary Form 4 XML document within the filing
    xml_url = _find_form4_xml_url(index_json_url)
    if not xml_url:
        logger.debug("No XML document found in filing index: %s", index_json_url)
        return []

    # Fetch and parse the XML
    resp = _sec_get(xml_url)
    trades = parse_form4_xml(
        xml_text=resp.text,
        cik=cik,
        ticker=ticker,
        company_name=company_name,
        filing_url=filing_url,
        filed_at=filed_at,
    )
    return trades


# ---------------------------------------------------------------------------
# Supabase persistence
# ---------------------------------------------------------------------------

def store_trades(trades: list[InsiderTrade], db: Any) -> int:
    """
    Upsert a list of InsiderTrade records into the Supabase `insider_trades` table.
    Uses (form4_url + transaction_date + insider_name + transaction_code) as
    the natural deduplication key.

    Args:
        trades: Parsed trade records
        db: DatabaseClient instance

    Returns:
        Count of records successfully stored
    """
    if not trades:
        return 0

    stored = 0
    for trade in trades:
        record = {
            "cik": trade.cik,
            "ticker": trade.ticker,
            "company_name": trade.company_name,
            "insider_name": trade.insider_name,
            "insider_title": trade.insider_title,
            "transaction_date": trade.transaction_date.isoformat(),
            "transaction_code": trade.transaction_code,
            "shares": trade.shares,
            "price_per_share": trade.price_per_share,
            "total_value": trade.total_value,
            "shares_owned_after": trade.shares_owned_after,
            "filing_timestamp": trade.filing_timestamp.isoformat(),
            "form4_url": trade.form4_url,
        }
        try:
            db.table("insider_trades").insert(record).execute()
            stored += 1
        except Exception as exc:
            # Unique constraint violations are expected (duplicate filings)
            logger.debug("Insert skipped (likely duplicate): %s", exc)

    logger.info("Stored %d/%d insider trade records", stored, len(trades))
    return stored
