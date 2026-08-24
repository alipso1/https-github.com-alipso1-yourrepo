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


# ─── SPN ─────────────────────────────────────────────────────────────────────
# Column mapping from Google Sheet SPN tab:
# 0  = Podcast (show name)
# 1  = Baked-In (net)
# 2  = Downloads per Episode
# 3  = CPM (gross)
# 4  = Minimum Endorsement Length
# 5  = Minimum Endorsement Monthly Investment
# 6  = Surround Social Endorsement Campaign Monthly Minimum
# 7  = DAI Available
# 8  = Frequency
# 9  = Audio / Video %
# 10 = Male / Female %
# 11 = Podcast Link
# 12 = Website
# 13 = Average Website Views per Month
# 14 = Website Banner (100% SOV monthly)
# 15 = Email Rates
# 16 = Email Subscribers
# 17 = Social Rates
# 18 = Social Audience Size
# 19 = Interview Rates Net
# 20 = Interview
# 21 = Other Rates Available

def build_spn_rates(rows):
    """Update rate values in spn.html showsData array."""
    import re

    if not os.path.exists("spn.html"):
        print("  spn.html not found, skipping")
        return None

    print(f"  Reading spn.html...")
    file_size = os.path.getsize("spn.html")
    print(f"  spn.html size: {file_size:,} bytes ({file_size//1024//1024}MB)")
    with open("spn.html", "r", encoding="utf-8") as f:
        html = f.read()
    print(f"  spn.html loaded successfully")

    def clean_num(v):
        """Convert spreadsheet value to JS number or null."""
        if not v or v.strip() in ("—", "null", "N/A", "", "-"):
            return "null"
        cleaned = v.replace("$", "").replace(",", "").strip()
        try:
            float(cleaned)
            return cleaned
        except ValueError:
            return "null"

    def clean_str(v):
        """Convert spreadsheet value to JS string or null."""
        if not v or v.strip() in ("—", "null", "N/A", ""):
            return "null"
        return v.strip()

    updated = 0
    for row in rows[1:]:  # skip header row
        if not any(row):
            continue
        show_name = val(row, 0)
        if not show_name or show_name.lower() in ("podcast", "show", ""):
            continue

        # Skip non-show rows
        skip_keywords = ["DAI", "Dynamic Ad Insertion", "Title Sponsorship", 
                         "Bulk Rate", "EKKL Network", "Live Read", "YouTube",
                         "Clips", "CPM", "Rate per"]
        if any(kw.lower() in show_name.lower() for kw in skip_keywords):
            continue

        # Map Google Sheet names to site names
        NAME_MAP = {
            "Charlie Kirk (Podcast)": "Charlie Kirk",
            "Erin Molan Clips": "Erin Molan Show",
            "Erin Molan": "Erin Molan Show",
            "Larry O'Connor": "Larry O\'Connor (Townhall Media)",
            "Joe Pags": "Joe Pags - Unshaken & Unafraid",
            "Lara Trump": "The Right View - Lara Trump",
            "The Right View": "The Right View - Lara Trump",
            "Timeless Wisdom": "Timeless Wisdom with Dennis Prager",
            "WHOA": "WHOA That\'s A Good Podcast",
            "Cam & Company": "Cam & Company (Bearing Arms)",
            "Bearing Arms": "Cam & Company (Bearing Arms)",
        }
        show_name = NAME_MAP.get(show_name, show_name)

        # Extract all rate fields
        baked_in_net    = clean_num(val(row, 1))
        downloads       = clean_num(val(row, 2))
        cpm_gross       = clean_num(val(row, 3))
        min_length      = clean_str(val(row, 4))
        min_monthly     = clean_num(val(row, 5))
        surround        = clean_num(val(row, 6))
        dai_avail       = clean_str(val(row, 7))
        freq            = clean_str(val(row, 8))
        av_pct          = clean_str(val(row, 9))
        gender          = clean_str(val(row, 10))
        pod_link        = clean_str(val(row, 11))
        website         = clean_str(val(row, 12))
        avg_web_views   = clean_num(val(row, 13))
        web_banner_net  = clean_num(val(row, 14))
        email_net       = clean_num(val(row, 15))
        email_subs      = clean_str(val(row, 16))
        social_rates    = clean_str(val(row, 17))
        social_audience = clean_str(val(row, 18))
        interview_net   = clean_num(val(row, 19))
        interview       = clean_num(val(row, 20))
        other           = clean_str(val(row, 21))

        # Format string values for JS (quoted or null)
        def js_str(v):
            if v == "null":
                return "null"
            return f'"{v}"'

        # Build the replacement showsData object for this show
        escaped_name = re.escape(show_name)
        pattern = re.compile(
            r'\{name:"' + escaped_name + r'",[^}]+\}',
            re.DOTALL
        )

        replacement = (
            '{' +
            f'name:"{show_name}",' +
            f'bakedIn:{baked_in_net},' +
            f'bakedInGross:{baked_in_net},' +
            f'downloads:{downloads},' +
            f'cpmNet:null,' +
            f'cpmGross:{cpm_gross},' +
            f'minEndLength:{js_str(min_length)},' +
            f'minMonthlyInvest:{min_monthly},' +
            f'surround:{surround},' +
            f'monthlyMin:{js_str(dai_avail)},' +
            f'daiAvail:{js_str(dai_avail)},' +
            f'freq:{js_str(freq)},' +
            f'avPct:{js_str(av_pct)},' +
            f'gender:{js_str(gender)},' +
            f'podLink:{js_str(pod_link)},' +
            f'website:{js_str(website)},' +
            f'webBannerNet:{web_banner_net},' +
            f'avgWebViews:{avg_web_views},' +
            f'webBannerSOV:null,' +
            f'emailNet:{email_net},' +
            f'emailGross:null,' +
            f'emailSubs:{js_str(email_subs)},' +
            f'socialRates:{js_str(social_rates)},' +
            f'socialAudience:{js_str(social_audience)},' +
            f'interviewNet:{interview_net},' +
            f'interview:{interview},' +
            f'other:{js_str(other)}'
        )

        # Preserve category and existing non-rate fields by doing targeted field updates
        # Only update numeric/rate fields to avoid breaking logos, links, etc.
        fields_to_update = {
            'bakedInGross': baked_in_net,
            'downloads': downloads,
            'cpmGross': cpm_gross,
            'minMonthlyInvest': min_monthly,
            'surround': surround,
        }

        show_updated = False
        for field, new_val in fields_to_update.items():
            if new_val == "null":
                continue
            field_pattern = re.compile(
                r'(\{name:"' + escaped_name + r'"[^}]*?' + re.escape(field) + r':)[^,}]+'
            )
            new_html, count = field_pattern.subn(r'\g<1>' + new_val, html)
            if count:
                html = new_html
                show_updated = True

        if show_updated:
            updated += 1
        else:
            print(f"  Could not find show: {show_name}")

    with open("spn.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✓ Updated {updated} shows in spn.html")
    return True

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
    ("SPN",           "spn.html",        None),  # handled separately
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
        if sheet_name == "SPN":
            print(f"  Processing SPN with {len(rows)} rows...")
            try:
                build_spn_rates(rows)
            except Exception as e:
                print(f"  ERROR processing SPN: {e}")
                import traceback
                traceback.print_exc()
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
