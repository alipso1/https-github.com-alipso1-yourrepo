#!/usr/bin/env python3
"""
Salem Rate Card Auto-Sync Script
Reads rate data from Google Sheets and rebuilds HTML rate card pages.
Run manually or via GitHub Actions (nightly).

Sheet ID: 1CxKKjfEIVz1YwvdkbIg7UHHa9O7QJmR_wXy0EU203Vw
"""

import csv
import io
import os
import re
import urllib.request

SHEET_ID = "1CxKKjfEIVz1YwvdkbIg7UHHa9O7QJmR_wXy0EU203Vw"

def fetch_sheet(sheet_name):
    """Fetch a tab from Google Sheets as a list of rows."""
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(sheet_name)}"
    try:
        with urllib.request.urlopen(url) as r:
            data = r.read().decode("utf-8")
        reader = csv.reader(io.StringIO(data))
        rows = [row for row in reader if any(cell.strip() for cell in row)]
        print(f"  Fetched '{sheet_name}': {len(rows)} rows")
        return rows
    except Exception as e:
        print(f"  ERROR fetching '{sheet_name}': {e}")
        return []

import urllib.parse

def val(row, col, default="—"):
    """Safely get a cell value from a row."""
    try:
        v = row[col].strip()
        return v if v else default
    except IndexError:
        return default

def html_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def read_template(filename):
    """Read an existing HTML file to extract the header/footer template."""
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

def replace_table_section(html, new_content, start_marker="<!-- SYNC_START -->", end_marker="<!-- SYNC_END -->"):
    """Replace content between sync markers."""
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    replacement = f"{start_marker}\n{new_content}\n{end_marker}"
    if pattern.search(html):
        return pattern.sub(replacement, html)
    else:
        # If markers don't exist, insert before save-toast div
        return html.replace('<div class="save-toast"', f"{start_marker}\n{new_content}\n{end_marker}\n\n" + '<div class="save-toast"')

# ─── MISC O&O ────────────────────────────────────────────────────────────────
def build_misc_table(rows):
    html = ['<table class="rate-table"><thead><tr><th>Property</th><th>Rate (CPM) NET</th><th>Rate (CPM) Gross</th><th>Subscribers</th><th>Notes</th></tr></thead><tbody>']
    for row in rows[1:]:  # skip header
        if not any(row):
            continue
        label = val(row, 0)
        if label.startswith("#") or label.lower() == "property":
            continue
        # Section headers have empty rate columns
        if val(row, 1) == "—" and val(row, 2) == "—" and val(row, 3) == "—":
            html.append(f'<tr class="section-header"><td colspan="5">{html_escape(label)}</td></tr>')
        else:
            html.append(f'<tr><td>{html_escape(label)}</td><td>{html_escape(val(row,1))}</td><td>{html_escape(val(row,2))}</td><td>{html_escape(val(row,3))}</td><td>{html_escape(val(row,4))}</td></tr>')
    html.append("</tbody></table>")
    return "\n".join(html)

# ─── LOCAL STATION ───────────────────────────────────────────────────────────
def build_local_table(rows):
    html = ['<table class="rate-table"><thead><tr><th>Tactic</th><th>Gross Rates</th><th>Hot Deals, Special Offers &amp; Promotions</th><th>Conferences, Concerts &amp; Special Events</th><th>Non-Profit &amp; Charitable Opportunities</th></tr></thead><tbody>']
    # Known clickable links
    LINKS = {
        "dedicated email rates (per station)": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=1000178295",
        "homepage takeover (per station)": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=920169529",
        "loyalty program promotion (per station)": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=920169529",
        "mobile app splash page sponsorship": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=1618078422",
        "mobile app splash page": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=1618078422",
        "sticky footer (per station)": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=1618078422",
        "streaming sponsorship": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=1618078422",
        "streaming": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=1618078422",
        "local station metrics": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=1618078422",
    }
    for row in rows[1:]:
        if not any(row):
            continue
        label = val(row, 0)
        if label.lower() in ("tactic", "property", ""):
            continue
        if label.lower() in LINKS:
            link = LINKS[label.lower()]
            html.append(f'<tr><td>{html_escape(label)}</td><td colspan="4"><a href="{link}" target="_blank" style="color:var(--gold);">Click Here</a></td></tr>')
        elif val(row,1) == "—" and val(row,2) == "—":
            html.append(f'<tr class="section-header"><td colspan="5">{html_escape(label)}</td></tr>')
        else:
            html.append(f'<tr><td>{html_escape(label)}</td><td>{html_escape(val(row,1))}</td><td>{html_escape(val(row,2))}</td><td>{html_escape(val(row,3))}</td><td>{html_escape(val(row,4))}</td></tr>')
    html.append("</tbody></table>")
    return "\n".join(html)

# ─── SALEM WEB NETWORK ───────────────────────────────────────────────────────
def build_swn_table(rows):
    html = ['<table class="rate-table"><thead><tr><th>Product</th><th>Pricing</th><th>Notes</th><th>Total Inventory</th><th>Assets Needed</th><th>Min. Buy</th></tr></thead><tbody>']
    for row in rows[1:]:
        if not any(row):
            continue
        label = val(row, 0)
        if label.lower() in ("product", ""):
            continue
        if val(row,1) == "—" and val(row,2) == "—":
            html.append(f'<tr class="section-header"><td colspan="6">{html_escape(label)}</td></tr>')
        else:
            html.append(f'<tr><td>{html_escape(label)}</td><td>{html_escape(val(row,1))}</td><td>{html_escape(val(row,2))}</td><td>{html_escape(val(row,3))}</td><td>{html_escape(val(row,4))}</td><td>{html_escape(val(row,5))}</td></tr>')
    html.append("</tbody></table>")
    return "\n".join(html)

# ─── SRN ─────────────────────────────────────────────────────────────────────
def build_srn_table(rows):
    html = ['<table class="rate-table"><thead><tr><th>Host / Product</th><th>Daypart</th><th>:60 NET</th><th>:30 NET</th><th>Min. Monthly</th><th>Podcast DLs</th><th>Affiliates</th></tr></thead><tbody>']
    for row in rows[1:]:
        if not any(row):
            continue
        label = val(row, 0)
        if label.lower() in ("host", "product", ""):
            continue
        if val(row,1) == "—" and val(row,2) == "—" and val(row,3) == "—":
            html.append(f'<tr class="section-header"><td colspan="7">{html_escape(label)}</td></tr>')
        else:
            html.append(f'<tr><td>{html_escape(label)}</td><td>{html_escape(val(row,1))}</td><td>{html_escape(val(row,2))}</td><td>{html_escape(val(row,3))}</td><td>{html_escape(val(row,4))}</td><td>{html_escape(val(row,5))}</td><td>{html_escape(val(row,6))}</td></tr>')
    html.append("</tbody></table>")
    return "\n".join(html)

# ─── STREAMING ───────────────────────────────────────────────────────────────
def build_streaming_table(rows):
    html = ['<table class="rate-table"><thead><tr><th>Product</th><th>NET CPM</th><th>Gross CPM</th><th>Monthly Min</th></tr></thead><tbody>']
    for row in rows[1:]:
        if not any(row):
            continue
        label = val(row, 0)
        if label.lower() in ("product", ""):
            continue
        if val(row,1) == "—" and val(row,2) == "—":
            html.append(f'<tr class="section-header"><td colspan="4">{html_escape(label)}</td></tr>')
        else:
            html.append(f'<tr><td>{html_escape(label)}</td><td>{html_escape(val(row,1))}</td><td>{html_escape(val(row,2))}</td><td>{html_escape(val(row,3))}</td></tr>')
    html.append("</tbody></table>")
    return "\n".join(html)

# ─── TOWNHALL ────────────────────────────────────────────────────────────────
def build_townhall_table(rows):
    html = ['<table class="rate-table"><thead><tr><th>Product</th><th>Pricing</th><th>Notes</th></tr></thead><tbody>']
    for row in rows[1:]:
        if not any(row):
            continue
        label = val(row, 0)
        if label.lower() in ("product", ""):
            continue
        if val(row,1) == "—" and val(row,2) == "—":
            html.append(f'<tr class="section-header"><td colspan="3">{html_escape(label)}</td></tr>')
        else:
            html.append(f'<tr><td>{html_escape(label)}</td><td>{html_escape(val(row,1))}</td><td>{html_escape(val(row,2))}</td></tr>')
    html.append("</tbody></table>")
    return "\n".join(html)

# ─── SNC ─────────────────────────────────────────────────────────────────────
def build_snc_table(rows):
    html = ['<table class="rate-table"><thead><tr><th>Product</th><th>15s</th><th>30s</th><th>60s</th></tr></thead><tbody>']
    for row in rows[1:]:
        if not any(row):
            continue
        label = val(row, 0)
        if label.lower() in ("product", ""):
            continue
        if val(row,1) == "—" and val(row,2) == "—" and val(row,3) == "—":
            html.append(f'<tr class="section-header"><td colspan="4">{html_escape(label)}</td></tr>')
        else:
            html.append(f'<tr><td>{html_escape(label)}</td><td>{html_escape(val(row,1))}</td><td>{html_escape(val(row,2))}</td><td>{html_escape(val(row,3))}</td></tr>')
    html.append("</tbody></table>")
    return "\n".join(html)

# ─── PARTHENON ───────────────────────────────────────────────────────────────
def build_parthenon_table(rows):
    html = ['<table class="rate-table"><thead><tr><th></th><th>Podcast</th><th>Weekly Rate</th><th>Weekly NET</th><th>Weekly Impr.</th><th>Frequency</th><th>Gender</th></tr></thead><tbody>']
    LOGOS = {
        "History Unplugged": "https://i.swncdn.com/lifeaudio/400w/podcast/show/59/image/638628804483235532-rss.webp",
        "Eyewitness History": "https://i.swncdn.com/lifeaudio/400w/podcast/show/72/image/638472888255448646-rss.webp",
        "Key Battles of American History": "https://i.swncdn.com/lifeaudio/400w/podcast/show/62/image/638620812451229471-rss.webp",
        "Beyond the Big Screen": "https://i.swncdn.com/lifeaudio/400w/podcast/show/60/image/637732617252616015-rss.webp",
        "History of the Papacy": "https://i.swncdn.com/lifeaudio/400w/podcast/show/61/image/638675352323163370-rss.webp",
        "This American President": "https://i.swncdn.com/lifeaudio/400w/podcast/show/69/image/638604396813125442-rss.webp",
        "Vlogging Through History": "https://i.swncdn.com/lifeaudio/400w/podcast/show/76/image/638585460628084349-rss.webp",
        "History of North America": "https://i.swncdn.com/lifeaudio/400w/podcast/show/141/image/638217504305560869-rss.webp",
    }
    for row in rows[1:]:
        if not any(row):
            continue
        label = val(row, 0)
        if label.lower() in ("podcast", ""):
            continue
        logo = LOGOS.get(label, "")
        logo_td = f'<td><img style="width:44px;height:44px;border-radius:7px;object-fit:cover;" src="{logo}" alt="" onerror="this.style.display=\'none\'"></td>' if logo else '<td></td>'
        html.append(f'<tr>{logo_td}<td>{html_escape(label)}</td><td>{html_escape(val(row,1))}</td><td>{html_escape(val(row,2))}</td><td>{html_escape(val(row,3))}</td><td>{html_escape(val(row,4))}</td><td>{html_escape(val(row,5))}</td></tr>')
    html.append("</tbody></table>")
    return "\n".join(html)

# ─── MAIN ────────────────────────────────────────────────────────────────────
PAGES = [
    ("Misc",          "misc.html",       build_misc_table),
    ("Local Station", "local.html",      build_local_table),
    ("Salem Web Network", "swn.html",    build_swn_table),
    ("SRN",           "srn.html",        build_srn_table),
    ("Streaming",     "streaming.html",  build_streaming_table),
    ("Townhall",      "townhall.html",   build_townhall_table),
    ("SNC",           "snc.html",        build_snc_table),
    ("Parthenon",     "parthenon.html",  build_parthenon_table),
]

def main():
    print("Salem Rate Card Sync")
    print("=" * 40)
    for sheet_name, filename, builder in PAGES:
        print(f"\nProcessing: {sheet_name} → {filename}")
        rows = fetch_sheet(sheet_name)
        if not rows:
            print(f"  Skipping (no data)")
            continue
        new_table = builder(rows)
        if not os.path.exists(filename):
            print(f"  File not found: {filename} (skipping)")
            continue
        html = read_template(filename)
        html = replace_table_section(html, new_table)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✓ Updated {filename}")
    print("\n✓ Sync complete!")

if __name__ == "__main__":
    main()
