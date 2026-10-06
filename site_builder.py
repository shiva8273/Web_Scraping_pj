import csv
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR   = Path(__file__).parent
OUTPUT_DIR = ROOT_DIR / "output"
SITE_DIR   = ROOT_DIR / "site"

CSV_PATH     = OUTPUT_DIR / "final_dataset.csv"
SUMMARY_PATH = OUTPUT_DIR / "summary_report.json"



def _h(value) -> str:
    """HTML-escape a value; return empty string for None / blank."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _star(rating) -> str:
    """Convert numeric rating (1-5) to filled/empty star characters."""
    try:
        n = int(rating)
        return "★" * n + "☆" * (5 - n)
    except (TypeError, ValueError):
        return ""


def _fmt_price(price) -> str:
    if price == "" or price is None:
        return "—"
    try:
        return f"£{float(price):.2f}"
    except ValueError:
        return _h(price)


def _fmt_tags(tags) -> str:
    if not tags:
        return ""
    return ", ".join(
        f'<span class="tag">{_h(t.strip())}</span>'
        for t in str(tags).split(",") if t.strip()
    )


def _avail_badge(avail) -> str:
    if not avail:
        return ""
    cls = "badge-in" if "in stock" in avail.lower() else "badge-out"
    return f'<span class="badge {cls}">{_h(avail)}</span>'


def _load_data() -> tuple[list[dict], dict]:
    records: list[dict] = []
    if CSV_PATH.exists():
        with CSV_PATH.open(encoding="utf-8") as fh:
            records = list(csv.DictReader(fh))

    summary: dict = {}
    if SUMMARY_PATH.exists():
        with SUMMARY_PATH.open(encoding="utf-8") as fh:
            summary = json.load(fh)

    return records, summary


# ── stylesheet ────────────────────────────────────────────────────────────────

CSS = """\
:root {
  --bg: #f8f9fb;
  --surface: #ffffff;
  --border: #e2e6ea;
  --primary: #2563eb;
  --primary-dark: #1d4ed8;
  --text: #1e293b;
  --muted: #64748b;
  --green: #16a34a;
  --red: #dc2626;
  --tag-bg: #eff6ff;
  --tag-color: #1d4ed8;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}
a { color: var(--primary); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── nav ── */
nav {
  background: var(--primary);
  color: #fff;
  padding: 0 1.5rem;
  display: flex;
  align-items: center;
  gap: 2rem;
  height: 56px;
}
nav .brand { font-weight: 700; font-size: 1.1rem; color: #fff; }
nav a { color: rgba(255,255,255,0.85); font-size: 0.92rem; }
nav a:hover { color: #fff; text-decoration: none; }

/* ── page wrapper ── */
.container { max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem; }
h1 { font-size: 1.7rem; margin-bottom: 0.25rem; }
.subtitle { color: var(--muted); font-size: 0.9rem; margin-bottom: 2rem; }

/* ── stat cards ── */
.stats { display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 2rem; }
.stat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.1rem 1.4rem;
  flex: 1 1 160px;
  min-width: 140px;
}
.stat-card .label { font-size: 0.78rem; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; }
.stat-card .value { font-size: 2rem; font-weight: 700; color: var(--primary); }
.stat-card .sub   { font-size: 0.78rem; color: var(--muted); }

/* ── section headers ── */
h2 { font-size: 1.2rem; margin: 2rem 0 0.75rem; }

/* ── tables ── */
.table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; background: var(--surface); }
table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
thead tr { background: #f1f5f9; }
th, td { padding: 0.6rem 0.8rem; text-align: left; border-bottom: 1px solid var(--border); }
th { font-weight: 600; color: var(--muted); white-space: nowrap; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #f8fafc; }
td.title a { color: var(--text); font-weight: 500; }
td.title a:hover { color: var(--primary); }

/* ── badges ── */
.badge { display: inline-block; padding: 0.15rem 0.45rem; border-radius: 999px; font-size: 0.75rem; font-weight: 600; }
.badge-in  { background: #dcfce7; color: var(--green); }
.badge-out { background: #fee2e2; color: var(--red); }

/* ── tags ── */
.tag { display: inline-block; background: var(--tag-bg); color: var(--tag-color); border-radius: 4px; padding: 0.05rem 0.4rem; font-size: 0.72rem; margin: 0.1rem; }

/* ── stars ── */
.stars { color: #f59e0b; letter-spacing: -1px; }

/* ── empty state ── */
.empty { text-align: center; padding: 4rem 2rem; color: var(--muted); }
.empty svg { display: block; margin: 0 auto 1rem; }

/* ── search ── */
.controls { display: flex; gap: 0.75rem; margin-bottom: 0.75rem; flex-wrap: wrap; }
.search-input {
  flex: 1 1 220px;
  padding: 0.45rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 0.875rem;
}
.search-input:focus { outline: 2px solid var(--primary); outline-offset: 1px; }

/* ── pagination ── */
.pagination { display: flex; gap: 0.4rem; justify-content: flex-end; margin-top: 0.75rem; flex-wrap: wrap; }
.pagination button {
  border: 1px solid var(--border);
  background: var(--surface);
  padding: 0.3rem 0.65rem;
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.8rem;
}
.pagination button.active { background: var(--primary); color: #fff; border-color: var(--primary); }
.pagination button:hover:not(.active) { background: #f1f5f9; }

/* ── footer ── */
footer { text-align: center; color: var(--muted); font-size: 0.8rem; padding: 2rem 0 1rem; }

/* ── responsive ── */
@media (max-width: 640px) {
  .stat-card .value { font-size: 1.5rem; }
  th, td { padding: 0.5rem 0.6rem; }
}
"""

# ── shared page chrome ─────────────────────────────────────────────────────────

def _nav(active: str) -> str:
    links = [
        ("index.html", "Home"),
        ("books.html", "Books"),
        ("quotes.html", "Quotes"),
    ]
    parts = ['<nav><span class="brand">📚 Web Scraper</span>']
    for href, label in links:
        if label == active:
            parts.append(f'<a href="{href}" style="color:#fff;font-weight:600">{label}</a>')
        else:
            parts.append(f'<a href="{href}">{label}</a>')
    parts.append("</nav>")
    return "\n".join(parts)


def _page(title: str, active: str, body: str, extra_js: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{_h(title)} – Web Scraper</title>
  <link rel="stylesheet" href="style.css"/>
</head>
<body>
{_nav(active)}
<div class="container">
{body}
</div>
<footer>
  Data scraped from <a href="https://books.toscrape.com" target="_blank" rel="noopener">Books to Scrape</a>
  and <a href="https://quotes.toscrape.com" target="_blank" rel="noopener">Quotes to Scrape</a>.
  These are public scraping practice sites.
</footer>
<script>
// ── shared table utilities ──────────────────────────────────────────────────
function initTable(tableId, searchId, paginId, pageSize) {{
  const table  = document.getElementById(tableId);
  if (!table) return;
  const tbody  = table.querySelector('tbody');
  const rows   = Array.from(tbody.querySelectorAll('tr'));
  const search = document.getElementById(searchId);
  const pagin  = document.getElementById(paginId);
  let current  = 1;
  let filtered = rows;

  function render() {{
    const start = (current - 1) * pageSize;
    const end   = start + pageSize;
    rows.forEach(r => r.style.display = 'none');
    filtered.slice(start, end).forEach(r => r.style.display = '');
    // pagination
    const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
    pagin.innerHTML = '';
    for (let i = 1; i <= pages; i++) {{
      const btn = document.createElement('button');
      btn.textContent = i;
      if (i === current) btn.classList.add('active');
      btn.addEventListener('click', () => {{ current = i; render(); }});
      pagin.appendChild(btn);
    }}
  }}

  if (search) {{
    search.addEventListener('input', () => {{
      const q = search.value.trim().toLowerCase();
      filtered = q ? rows.filter(r => r.textContent.toLowerCase().includes(q)) : rows;
      current = 1;
      render();
    }});
  }}
  render();
}}
{extra_js}
</script>
</body>
</html>"""


# ── empty state ───────────────────────────────────────────────────────────────

def _empty(message: str) -> str:
    return f"""<div class="empty">
  <svg width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="#94a3b8" stroke-width="1.5">
    <path stroke-linecap="round" stroke-linejoin="round"
      d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
  </svg>
  <p>{_h(message)}</p>
</div>"""


# ── index.html ────────────────────────────────────────────────────────────────

def _build_index(records: list[dict], summary: dict, updated_at: str) -> str:
    totals = summary.get("totals", {})
    src    = summary.get("sources", {})

    books_count  = sum(1 for r in records if r.get("source") == "Books to Scrape")
    quotes_count = sum(1 for r in records if r.get("source") == "Quotes to Scrape")

    stat_cards = f"""
<div class="stats">
  <div class="stat-card">
    <div class="label">Total records</div>
    <div class="value">{totals.get('total_final_records', len(records))}</div>
  </div>
  <div class="stat-card">
    <div class="label">Books</div>
    <div class="value">{books_count}</div>
    <div class="sub">from Books to Scrape</div>
  </div>
  <div class="stat-card">
    <div class="label">Quotes</div>
    <div class="value">{quotes_count}</div>
    <div class="sub">from Quotes to Scrape</div>
  </div>
  <div class="stat-card">
    <div class="label">Duplicates removed</div>
    <div class="value">{totals.get('total_duplicates_removed', '—')}</div>
  </div>
  <div class="stat-card">
    <div class="label">Rejected</div>
    <div class="value">{totals.get('total_rejected_validation', '—')}</div>
    <div class="sub">failed validation</div>
  </div>
</div>"""

    # recent books (up to 10)
    books  = [r for r in records if r.get("source") == "Books to Scrape"][:10]
    quotes = [r for r in records if r.get("source") == "Quotes to Scrape"][:5]

    if not records:
        data_section = _empty("No data found. Run the scraper to generate results.")
    else:
        # mini book table
        book_rows = ""
        for r in books:
            book_rows += f"""<tr>
  <td class="title"><a href="{_h(r.get('source_url',''))}" target="_blank" rel="noopener">{_h(r.get('name_or_title',''))}</a></td>
  <td>{_h(r.get('category',''))}</td>
  <td>{_fmt_price(r.get('price'))}</td>
  <td><span class="stars">{_star(r.get('rating'))}</span></td>
  <td>{_avail_badge(r.get('availability',''))}</td>
</tr>"""

        # mini quote list
        quote_items = ""
        for r in quotes:
            quote_items += f"""<tr>
  <td>{_h(r.get('name_or_title',''))}</td>
  <td>{_h(r.get('author',''))}</td>
  <td>{_fmt_tags(r.get('tags',''))}</td>
</tr>"""

        data_section = f"""
<h2>Recent Books <a href="books.html" style="font-size:.85rem;font-weight:400">View all →</a></h2>
<div class="table-wrap">
  <table><thead><tr>
    <th>Title</th><th>Category</th><th>Price</th><th>Rating</th><th>Availability</th>
  </tr></thead>
  <tbody>{book_rows}</tbody></table>
</div>

<h2 style="margin-top:2rem">Recent Quotes <a href="quotes.html" style="font-size:.85rem;font-weight:400">View all →</a></h2>
<div class="table-wrap">
  <table><thead><tr>
    <th>Quote</th><th>Author</th><th>Tags</th>
  </tr></thead>
  <tbody>{quote_items}</tbody></table>
</div>"""

    body = f"""
<h1>Web Scraper Results</h1>
<p class="subtitle">Last updated: <strong>{_h(updated_at)}</strong></p>
{stat_cards}
{data_section}
"""
    return _page("Home", "Home", body)


# ── books.html ────────────────────────────────────────────────────────────────

def _build_books(records: list[dict]) -> str:
    books = [r for r in records if r.get("source") == "Books to Scrape"]

    if not books:
        body = f"<h1>Books</h1>{_empty('No book records found.')}"
        return _page("Books", "Books", body)

    rows = ""
    for r in books:
        rows += f"""<tr>
  <td class="title"><a href="{_h(r.get('source_url',''))}" target="_blank" rel="noopener">{_h(r.get('name_or_title',''))}</a></td>
  <td>{_h(r.get('category',''))}</td>
  <td style="white-space:nowrap">{_fmt_price(r.get('price'))}</td>
  <td><span class="stars">{_star(r.get('rating'))}</span></td>
  <td>{_avail_badge(r.get('availability',''))}</td>
</tr>"""

    body = f"""
<h1>Books</h1>
<p class="subtitle">{len(books):,} books scraped from <a href="https://books.toscrape.com" target="_blank" rel="noopener">Books to Scrape</a></p>
<div class="controls">
  <input class="search-input" id="book-search" type="search" placeholder="Filter by title, category…"/>
</div>
<div class="table-wrap">
  <table id="book-table">
    <thead><tr>
      <th>Title</th><th>Category</th><th>Price</th><th>Rating</th><th>Availability</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
<div class="pagination" id="book-pagin"></div>
"""
    js = "initTable('book-table','book-search','book-pagin',25);"
    return _page("Books", "Books", body, extra_js=js)


# ── quotes.html ───────────────────────────────────────────────────────────────

def _build_quotes(records: list[dict]) -> str:
    quotes = [r for r in records if r.get("source") == "Quotes to Scrape"]

    if not quotes:
        body = f"<h1>Quotes</h1>{_empty('No quote records found.')}"
        return _page("Quotes", "Quotes", body)

    rows = ""
    for r in quotes:
        author_url = _h(r.get("source_url", ""))
        author_name = _h(r.get("author", ""))
        author_cell = (
            f'<a href="{author_url}" target="_blank" rel="noopener">{author_name}</a>'
            if author_url else author_name
        )
        rows += f"""<tr>
  <td style="max-width:420px">{_h(r.get('name_or_title',''))}</td>
  <td style="white-space:nowrap">{author_cell}</td>
  <td>{_fmt_tags(r.get('tags',''))}</td>
</tr>"""

    body = f"""
<h1>Quotes</h1>
<p class="subtitle">{len(quotes):,} quotes scraped from <a href="https://quotes.toscrape.com" target="_blank" rel="noopener">Quotes to Scrape</a></p>
<div class="controls">
  <input class="search-input" id="quote-search" type="search" placeholder="Filter by quote, author, tag…"/>
</div>
<div class="table-wrap">
  <table id="quote-table">
    <thead><tr>
      <th>Quote</th><th>Author</th><th>Tags</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
<div class="pagination" id="quote-pagin"></div>
"""
    js = "initTable('quote-table','quote-search','quote-pagin',25);"
    return _page("Quotes", "Quotes", body, extra_js=js)


# ── main ──────────────────────────────────────────────────────────────────────

def build_site() -> None:
    SITE_DIR.mkdir(exist_ok=True)

    records, summary = _load_data()

    # Derive "last updated" from summary or fall back to now
    finished = summary.get("pipeline_finished_at")
    if finished:
        try:
            dt = datetime.fromisoformat(finished)
            updated_at = dt.strftime("%Y-%m-%d %H:%M UTC")
        except ValueError:
            updated_at = finished
    else:
        updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    (SITE_DIR / "style.css").write_text(CSS, encoding="utf-8")
    (SITE_DIR / "index.html").write_text(_build_index(records, summary, updated_at), encoding="utf-8")
    (SITE_DIR / "books.html").write_text(_build_books(records), encoding="utf-8")
    (SITE_DIR / "quotes.html").write_text(_build_quotes(records), encoding="utf-8")

    print(f"Site built -> {SITE_DIR.resolve()}")
    print(f"  index.html  ({len(records)} records, updated {updated_at})")
    print(f"  books.html  ({sum(1 for r in records if r.get('source')=='Books to Scrape')} books)")
    print(f"  quotes.html ({sum(1 for r in records if r.get('source')=='Quotes to Scrape')} quotes)")
    print(f"  style.css")


if __name__ == "__main__":
    build_site()
