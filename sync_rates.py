#!/usr/bin/env python3
"""
Salem Rate Card Auto-Sync Script
Reads rate data from SharePoint Excel file via Microsoft Graph API
and rebuilds HTML rate card pages.

Credentials stored as GitHub Secrets:
  AZURE_TENANT_ID
  AZURE_CLIENT_ID  
  AZURE_CLIENT_SECRET
  SHAREPOINT_FILE_ID
"""

import csv
import io
import json
import os
import re
import urllib.request
import urllib.parse

# ─── MICROSOFT GRAPH AUTH ────────────────────────────────────────────────────
TENANT_ID     = os.environ.get('AZURE_TENANT_ID', 'a41ef9fc-f3d8-45aa-a36e-9b2d13d2d973')
CLIENT_ID     = os.environ.get('AZURE_CLIENT_ID', '2c9dc1b8-68df-41ab-a009-147d54565669')
CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET', '')
FILE_ID       = os.environ.get('SHAREPOINT_FILE_ID', '0993E18C-BF7F-4D67-80CA-A6AB35FC7E6F')
SITE_ID       = os.environ.get('SHAREPOINT_SITE_ID', '')  # will be discovered

def get_access_token():
    """Get OAuth2 access token from Azure AD."""
    url = f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token'
    data = urllib.parse.urlencode({
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'scope': 'https://graph.microsoft.com/.default'
    }).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())['access_token']

def graph_request(token, path):
    """Make a Microsoft Graph API request."""
    url = f'https://graph.microsoft.com/v1.0{path}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def get_sheet_data(token, sheet_name):
    """Fetch worksheet data from SharePoint Excel file via Graph API."""
    try:
        # Get used range from the worksheet
        path = f'/drives/root/items/{FILE_ID}/workbook/worksheets/{urllib.parse.quote(sheet_name)}/usedRange'
        
        # First try to find the file via site
        if SITE_ID:
            path = f'/sites/{SITE_ID}/drive/items/{FILE_ID}/workbook/worksheets/{urllib.parse.quote(sheet_name)}/usedRange'
        
        data = graph_request(token, path)
        values = data.get('values', [])
        print(f"  Fetched '{sheet_name}': {len(values)} rows")
        return values
    except Exception as e:
        print(f"  ERROR fetching '{sheet_name}': {e}")
        return []

def find_file(token):
    """Search for the rate card file in SharePoint."""
    try:
        # Search across all drives
        result = graph_request(token, f"/me/drive/items/{FILE_ID}")
        return result
    except:
        pass
    
    try:
        # Try via site
        result = graph_request(token, f"/sites/salemcommunications.sharepoint.com:/sites/DIGMktg")
        site_id = result['id']
        print(f"  Found site: {site_id}")
        return site_id
    except Exception as e:
        print(f"  Could not find site: {e}")
        return None

# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────
def val(row, col, default="—"):
    try:
        v = str(row[col]).strip() if row[col] is not None else ""
        return v if v and v != "None" else default
    except IndexError:
        return default

def html_escape(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def read_template(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

def replace_table_section(html, new_content):
    start_marker = "<!-- SYNC_START -->"
    end_marker = "<!-- SYNC_END -->"
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    replacement = f"{start_marker}\n{new_content}\n{end_marker}"
    if pattern.search(html):
        return pattern.sub(replacement, html)
    else:
        return html.replace('<div class="save-toast"', f"{start_marker}\n{new_content}\n{end_marker}\n\n" + '<div class="save-toast"')

# ─── TABLE BUILDERS ───────────────────────────────────────────────────────────
def build_misc_table(rows):
    html = ['<table class="rate-table"><thead><tr><th>Property</th><th>Rate (CPM) NET</th><th>Rate (CPM) Gross</th><th>Subscribers</th><th>Notes</th></tr></thead><tbody>']
    for row in rows[1:]:
        if not any(str(c).strip() for c in row if c is not None):
            continue
        label = val(row, 0)
        if not label or label.lower() in ("property", ""):
            continue
        if val(row, 1) == "—" and val(row, 2) == "—" and val(row, 3) == "—":
            html.append(f'<tr class="section-header"><td colspan="5">{html_escape(label)}</td></tr>')
        else:
            html.append(f'<tr><td>{html_escape(label)}</td><td>{html_escape(val(row,1))}</td><td>{html_escape(val(row,2))}</td><td>{html_escape(val(row,3))}</td><td>{html_escape(val(row,4))}</td></tr>')
    html.append("</tbody></table>")
    return "\n".join(html)

def build_local_table(rows):
    LINKS = {
        "dedicated email rates (per station)": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=1000178295",
        "homepage takeover (per station)": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=920169529",
        "loyalty program promotion (per station)": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=920169529",
        "mobile app splash page sponsorship": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=1618078422",
        "mobile app splash page": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=1618078422",
        "sticky footer (per station)": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=1618078422",
        "streaming sponsorship": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=1618078422",
        "local station metrics": "https://docs.google.com/spreadsheets/d/15E4aYnMG__Cpk7kpT9cE3bEwmE-uSp6-xnWu38Rlffs/edit#gid=1618078422",
    }
    html = ['<table class="rate-table"><thead><tr><th>Tactic</th><th>Gross Rates</th><th>Hot Deals, Special Offers &amp; Promotions</th><th>Conferences, Concerts &amp; Special Events</th><th>Non-Profit &amp; Charitable Opportunities</th></tr></thead><tbody>']
    for row in rows[1:]:
        if not any(str(c).strip() for c in row if c is not None):
            continue
        label = val(row, 0)
        if not label or label.lower() in ("tactic", ""):
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

def build_swn_table(rows):
    html = ['<table class="rate-table"><thead><tr><th>Product</th><th>Pricing</th><th>Notes</th><th>Total Inventory</th><th>Assets Needed</th><th>Min. Buy</th></tr></thead><tbody>']
    for row in rows[1:]:
        if not any(str(c).strip() for c in row if c is not None):
            continue
        label = val(row, 0)
        if not label or label.lower() in ("product", ""):
            continue
        if val(row,1) == "—" and val(row,2) == "—":
            html.append(f'<tr class="section-header"><td colspan="6">{html_escape(label)}</td></tr>')
        else:
            html.append(f'<tr><td>{html_escape(label)}</td><td>{html_escape(val(row,1))}</td><td>{html_escape(val(row,2))}</td><td>{html_escape(val(row,3))}</td><td>{html_escape(val(row,4))}</td><td>{html_escape(val(row,5))}</td></tr>')
    html.append("</tbody></table>")
    return "\n".join(html)

def build_srn_table(rows):
    html = ['<table class="rate-table"><thead><tr><th>Host / Product</th><th>Daypart</th><th>:60 NET</th><th>:30 NET</th><th>Min. Monthly</th><th>Podcast DLs</th><th>Affiliates</th></tr></thead><tbody>']
    for row in rows[1:]:
        if not any(str(c).strip() for c in row if c is not None):
            continue
        label = val(row, 0)
        if not label or label.lower() in ("host", "product", ""):
            continue
        if val(row,1) == "—" and val(row,2) == "—" and val(row,3) == "—":
            html.append(f'<tr class="section-header"><td colspan="7">{html_escape(label)}</td></tr>')
        else:
            html.append(f'<tr><td>{html_escape(label)}</td><td>{html_escape(val(row,1))}</td><td>{html_escape(val(row,2))}</td><td>{html_escape(val(row,3))}</td><td>{html_escape(val(row,4))}</td><td>{html_escape(val(row,5))}</td><td>{html_escape(val(row,6))}</td></tr>')
    html.append("</tbody></table>")
    return "\n".join(html)

def build_streaming_table(rows):
    html = ['<table class="rate-table"><thead><tr><th>Product</th><th>NET CPM</th><th>Gross CPM</th><th>Monthly Min</th></tr></thead><tbody>']
    for row in rows[1:]:
        if not any(str(c).strip() for c in row if c is not None):
            continue
        label = val(row, 0)
        if not label or label.lower() in ("product", ""):
            continue
        if val(row,1) == "—" and val(row,2) == "—":
            html.append(f'<tr class="section-header"><td colspan="4">{html_escape(label)}</td></tr>')
        else:
            html.append(f'<tr><td>{html_escape(label)}</td><td>{html_escape(val(row,1))}</td><td>{html_escape(val(row,2))}</td><td>{html_escape(val(row,3))}</td></tr>')
    html.append("</tbody></table>")
    return "\n".join(html)

def build_townhall_table(rows):
    html = ['<table class="rate-table"><thead><tr><th>Product</th><th>Pricing</th><th>Notes</th></tr></thead><tbody>']
    for row in rows[1:]:
        if not any(str(c).strip() for c in row if c is not None):
            continue
        label = val(row, 0)
        if not label or label.lower() in ("product", ""):
            continue
        if val(row,1) == "—" and val(row,2) == "—":
            html.append(f'<tr class="section-header"><td colspan="3">{html_escape(label)}</td></tr>')
        else:
            html.append(f'<tr><td>{html_escape(label)}</td><td>{html_escape(val(row,1))}</td><td>{html_escape(val(row,2))}</td></tr>')
    html.append("</tbody></table>")
    return "\n".join(html)

def build_snc_table(rows):
    html = ['<table class="rate-table"><thead><tr><th>Product</th><th>15s</th><th>30s</th><th>60s</th></tr></thead><tbody>']
    for row in rows[1:]:
        if not any(str(c).strip() for c in row if c is not None):
            continue
        label = val(row, 0)
        if not label or label.lower() in ("product", ""):
            continue
        if val(row,1) == "—" and val(row,2) == "—" and val(row,3) == "—":
            html.append(f'<tr class="section-header"><td colspan="4">{html_escape(label)}</td></tr>')
        else:
            html.append(f'<tr><td>{html_escape(label)}</td><td>{html_escape(val(row,1))}</td><td>{html_escape(val(row,2))}</td><td>{html_escape(val(row,3))}</td></tr>')
    html.append("</tbody></table>")
    return "\n".join(html)

def build_parthenon_table(rows):
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
    html = ['<table class="rate-table"><thead><tr><th></th><th>Podcast</th><th>Weekly Rate</th><th>Weekly NET</th><th>Weekly Impr.</th><th>Frequency</th><th>Gender</th></tr></thead><tbody>']
    for row in rows[1:]:
        if not any(str(c).strip() for c in row if c is not None):
            continue
        label = val(row, 0)
        if not label or label.lower() in ("podcast", ""):
            continue
        logo = LOGOS.get(label, "")
        logo_td = f'<td><img style="width:44px;height:44px;border-radius:7px;object-fit:cover;" src="{logo}" alt="" onerror="this.style.display=\'none\'"></td>' if logo else '<td></td>'
        html.append(f'<tr>{logo_td}<td>{html_escape(label)}</td><td>{html_escape(val(row,1))}</td><td>{html_escape(val(row,2))}</td><td>{html_escape(val(row,3))}</td><td>{html_escape(val(row,4))}</td><td>{html_escape(val(row,5))}</td></tr>')
    html.append("</tbody></table>")
    return "\n".join(html)

def build_spn_rates(rows):
    """Update rate values in spn.html showsData array."""
    if not os.path.exists("spn.html"):
        print("  spn.html not found, skipping")
        return None

    print(f"  Reading spn.html...")
    with open("spn.html", "r", encoding="utf-8") as f:
        html = f.read()
    print(f"  spn.html loaded successfully")

    NAME_MAP = {
        "Charlie Kirk (Podcast)": "Charlie Kirk",
        "Charlie Kirk Live Read (RAV & Streaming)": None,
        "Charlie Kirk (YouTube)": None,
        "Erin Molan Clips": None,
        "Dynamic Ad Insertion (DAI) - $29 CPM": None,
        "DAI Bulk Rate - $20 CPM (includes Podscribe) - 500K+ imp": None,
        "Title Sponsorship - Baked-In rate per week": None,
        "EKKL Network": None,
        "Erin Molan": "Erin Molan Show",
        "Larry O'Connor": "Larry O\\'Connor (Townhall Media)",
        "Joe Pags": "Joe Pags - Unshaken & Unafraid",
        "Lara Trump": "The Right View - Lara Trump",
        "The Right View": "The Right View - Lara Trump",
        "Timeless Wisdom": "Timeless Wisdom with Dennis Prager",
        "WHOA": "WHOA That\\'s A Good Podcast",
        "Cam & Company": "Cam & Company (Bearing Arms)",
        "Bearing Arms": "Cam & Company (Bearing Arms)",
    }

    def clean_num(v):
        if not v or str(v).strip() in ("—", "null", "N/A", "", "-", "None"):
            return "null"
        cleaned = str(v).replace("$", "").replace(",", "").strip()
        try:
            float(cleaned)
            return cleaned
        except ValueError:
            return "null"

    updated = 0
    for row in rows[1:]:
        if not any(str(c).strip() for c in row if c is not None):
            continue
        show_name = val(row, 0)
        if not show_name or show_name.lower() in ("podcast", "show", ""):
            continue

        mapped = NAME_MAP.get(show_name, show_name)
        if mapped is None:
            continue
        show_name = mapped

        baked_in_net = clean_num(val(row, 1))
        downloads    = clean_num(val(row, 2))
        cpm_gross    = clean_num(val(row, 3))
        min_monthly  = clean_num(val(row, 5))
        surround     = clean_num(val(row, 6))

        fields_to_update = {
            'bakedInGross': baked_in_net,
            'downloads':    downloads,
            'cpmGross':     cpm_gross,
            'minMonthlyInvest': min_monthly,
            'surround':     surround,
        }

        escaped_name = re.escape(show_name)
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
    ("Misc",              "misc.html",       build_misc_table),
    ("Local Station",     "local.html",      build_local_table),
    ("Salem Web Network", "swn.html",        build_swn_table),
    ("SRN",               "srn.html",        build_srn_table),
    ("Streaming",         "streaming.html",  build_streaming_table),
    ("Townhall",          "townhall.html",   build_townhall_table),
    ("SNC",               "snc.html",        build_snc_table),
    ("Parthenon",         "parthenon.html",  build_parthenon_table),
    ("SPN",               "spn.html",        None),
]

def main():
    print("Salem Rate Card Sync")
    print("=" * 40)

    # Debug: check if credentials are present
    print(f"AZURE_TENANT_ID present: {bool(os.environ.get('AZURE_TENANT_ID'))}")
    print(f"AZURE_CLIENT_ID present: {bool(os.environ.get('AZURE_CLIENT_ID'))}")
    print(f"AZURE_CLIENT_SECRET present: {bool(os.environ.get('AZURE_CLIENT_SECRET'))}")

    # Get access token
    print("Authenticating with Microsoft Graph...")
    try:
        token = get_access_token()
        print("✓ Authenticated successfully")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        print("Falling back to Google Sheets...")
        run_google_sheets_fallback()
        return

    # Find the SharePoint site
    try:
        site_data = graph_request(token, "/sites/salemcommunications.sharepoint.com:/sites/DIGMktg")
        site_id = site_data['id']
        print(f"✓ Found SharePoint site: {site_id}")
    except Exception as e:
        print(f"✗ Could not find SharePoint site: {e}")
        print("Falling back to Google Sheets...")
        run_google_sheets_fallback()
        return

    # Find the Excel file
    try:
        # Search for the file
        drive_data = graph_request(token, f"/sites/{site_id}/drive/root/search(q='SMR O&O Rate Card')")
        files = drive_data.get('value', [])
        if not files:
            raise Exception("File not found")
        file_item = files[0]
        file_id = file_item['id']
        print(f"✓ Found file: {file_item['name']} (ID: {file_id})")
    except Exception as e:
        print(f"✗ Could not find Excel file: {e}")
        print("Trying with known file ID...")
        file_id = FILE_ID

    # Process each sheet
    for sheet_name, filename, builder in PAGES:
        print(f"\nProcessing: {sheet_name} → {filename}")
        try:
            path = f"/sites/{site_id}/drive/items/{file_id}/workbook/worksheets/{urllib.parse.quote(sheet_name)}/usedRange"
            data = graph_request(token, path)
            rows = data.get('values', [])
            print(f"  Fetched '{sheet_name}': {len(rows)} rows")
        except Exception as e:
            print(f"  ERROR fetching '{sheet_name}': {e}")
            continue

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

def run_google_sheets_fallback():
    """Fallback to Google Sheets if SharePoint auth fails."""
    import urllib.request as ur
    SHEET_ID = "1CxKKjfEIVz1YwvdkbIg7UHHa9O7QJmR_wXy0EU203Vw"

    def fetch_sheet(sheet_name):
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(sheet_name)}"
        try:
            with ur.urlopen(url) as r:
                data = r.read().decode("utf-8")
            import csv, io
            reader = csv.reader(io.StringIO(data))
            rows = [row for row in reader if any(cell.strip() for cell in row)]
            print(f"  Fetched '{sheet_name}' from Google Sheets: {len(rows)} rows")
            return rows
        except Exception as e:
            print(f"  ERROR: {e}")
            return []

    print("Salem Rate Card Sync (Google Sheets Fallback)")
    print("=" * 40)
    for sheet_name, filename, builder in PAGES:
        print(f"\nProcessing: {sheet_name} → {filename}")
        rows = fetch_sheet(sheet_name)
        if not rows:
            continue
        if sheet_name == "SPN":
            print(f"  Processing SPN with {len(rows)} rows...")
            try:
                build_spn_rates(rows)
            except Exception as e:
                print(f"  ERROR: {e}")
            continue
        new_table = builder(rows)
        if not os.path.exists(filename):
            continue
        html = read_template(filename)
        html = replace_table_section(html, new_table)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✓ Updated {filename}")
    print("\n✓ Sync complete!")

if __name__ == "__main__":
    main()
