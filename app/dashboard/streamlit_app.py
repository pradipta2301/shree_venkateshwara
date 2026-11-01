import streamlit as st
import pandas as pd
import plotly.express as px
import os
import base64
import textwrap
from datetime import datetime

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Tender Intelligence Platform",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# IMAGE TO BASE64 HELPER (For custom HTML Header)
# ============================================================
@st.cache_data
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return ""

bg_image_b64 = get_base64_of_bin_file("Gemini_Generated_Image.png")

# ============================================================
# PREMIUM UI / CSS
# ============================================================
css = """
<style>
/* ---------- Global ---------- */
.stApp { background-color: #f8fafc; }
.block-container { padding-top: 1.2rem !important; padding-bottom: 2rem !important; max-width: 1600px; }

/* Hide Sidebar toggle */
[data-testid="collapsedControl"] { display: none; }

/* ---------- Filter Labels ---------- */
.stTextInput label p, .stMultiSelect label p, .stDateInput label p, .stSelectbox label p {
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    color: #020617 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ---------- KPI cards ---------- */
.kpi-card {
    background: white; border: 1px solid #e2e8f0; border-radius: 12px;
    padding: 15px; min-height: 90px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    display: flex; flex-direction: column; justify-content: center;
}
.kpi-icon { font-size: 1.2rem; margin-bottom: 5px; }
.kpi-label { font-size: 0.75rem; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
.kpi-value { font-size: 1.6rem; color: #0f172a; font-weight: 800; line-height: 1.2; }
.kpi-blue { border-top: 4px solid #2563eb; }
.kpi-green { border-top: 4px solid #16a34a; }
.kpi-orange { border-top: 4px solid #f59e0b; }
.kpi-cyan { border-top: 4px solid #0891b2; }

/* ---------- Revolving Animation ---------- */
.revolving-container { position: relative; height: 50px; overflow: hidden; }
.revolve-item { position: absolute; width: 100%; top: 0; left: 0; animation: flip 6s infinite ease-in-out; }
.item-2 { animation-delay: 3s; opacity: 0; transform: translateY(15px); }

@keyframes flip {
    0%, 40% { opacity: 1; transform: translateY(0px); }
    45%, 50% { opacity: 0; transform: translateY(-15px); }
    90%, 95% { opacity: 0; transform: translateY(15px); }
    100% { opacity: 1; transform: translateY(0px); }
}

/* ---------- Tender Cards (SaaS Feed UI) ---------- */
.tender-card {
    background: white; border-radius: 12px; padding: 20px 24px;
    margin-bottom: 16px; border: 1px solid #e2e8f0; border-left: 5px solid #2563eb;
    box-shadow: 0 4px 10px rgba(0,0,0,0.03); transition: all 0.2s ease;
}
.tender-card:hover { transform: translateY(-3px); box-shadow: 0 10px 20px rgba(0,0,0,0.08); }
.tc-dept-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.tc-dept { font-size: 0.85rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }

/* Urgency Badges */
.badge-red { background: #fee2e2; color: #dc2626; padding: 3px 10px; border-radius: 6px; font-weight: 700; font-size: 0.78rem; }
.badge-light-red { background: #ffedd5; color: #ea580c; padding: 3px 10px; border-radius: 6px; font-weight: 700; font-size: 0.78rem; }
.badge-yellow { background: #fef9c3; color: #ca8a04; padding: 3px 10px; border-radius: 6px; font-weight: 700; font-size: 0.78rem; }
.badge-green { background: #dcfce7; color: #16a34a; padding: 3px 10px; border-radius: 6px; font-weight: 700; font-size: 0.78rem; }
.badge-gray { background: #f1f5f9; color: #64748b; padding: 3px 10px; border-radius: 6px; font-weight: 700; font-size: 0.78rem; }

.tc-title { font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-bottom: 10px; line-height: 1.4; }
.tc-meta { font-size: 0.85rem; color: #475569; margin-bottom: 12px; display: flex; gap: 15px; align-items: center; }
.tc-tag { background: #f1f5f9; padding: 6px 12px; border-radius: 8px; font-weight: 600; color: #334155; display: inline-block; line-height: 1.4; }
.tc-loc { font-size: 0.9rem; color: #334155; background: #f8fafc; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #f1f5f9;}
.tc-summary { font-size: 0.95rem; color: #1e293b; margin-bottom: 18px; line-height: 1.5; font-weight: 500; }
.tc-grid { 
    display: grid; grid-template-columns: repeat(5, 1fr) auto; gap: 10px; 
    align-items: center; background: #f8fafc; padding: 12px 16px; border-radius: 8px; border: 1px solid #f1f5f9;
}
.tc-stat-label { font-size: 0.75rem; color: #64748b; font-weight: 600; text-transform: uppercase; margin-bottom: 2px;}
.tc-stat-val { font-size: 0.95rem; color: #0f172a; font-weight: 700; }
.tc-btn { 
    background: #2563eb; color: white !important; padding: 10px 20px; 
    border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 0.9rem; transition: 0.2s;
    display: inline-block;
}
.tc-btn:hover { background: #1d4ed8; }

/* Tabs overriding */
button[data-baseweb="tab"] { font-weight: 700 !important; opacity: 1 !important; font-size: 1.1rem !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: #2563eb !important; }
</style>
"""
st.markdown(css.replace('\n', ' '), unsafe_allow_html=True)


# ============================================================
# DATA LOADING
# ============================================================
@st.cache_data(ttl=600)
def load_data():
    file_path = "odisha_tenders.xlsx"
    if not os.path.exists(file_path):
        file_path = "odisha_tenders.xlsx"

    try:
        df = pd.read_excel(file_path)

        if "Tender Value" in df.columns:
            df["Tender Value"] = pd.to_numeric(df["Tender Value"], errors="coerce").fillna(0)
            
        if "EMD" in df.columns:
            df["EMD"] = pd.to_numeric(df["EMD"], errors="coerce").fillna(0)

        for date_col in ["Published Date", "Opening Date", "Closing Date"]:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        if "Tender No" in df.columns:
            def identify_source(t_no):
                return "GeM" if str(t_no).strip().upper().startswith("GEM") else "NIC / State Portal"
            idx = df.columns.get_loc("Tender No") + 1
            df.insert(idx, "Source Portal", df["Tender No"].apply(identify_source))

        def get_valid_link(row):
            link = str(row.get("Link", "")).strip()
            t_no = str(row.get("Tender No", "")).strip()
            if link.startswith("http"): return link
            if t_no.upper().startswith("GEM"): return f"https://bidplus.gem.gov.in/all-bids?q={t_no}"
            return "https://tenders.odisha.gov.in"

        if "Link" in df.columns:
            df["Link"] = df.apply(get_valid_link, axis=1)
        else:
            df["Link"] = "https://bidplus.gem.gov.in/all-bids"

        return df

    except Exception as e:
        st.error(f"Failed to load Excel file: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No tender data found. Please keep the Excel file in the same folder as this Streamlit application.")
    st.stop()


# ============================================================
# CUSTOM HERO HEADER
# ============================================================
header_html = f"""
<div style="
    position: relative; 
    height: 400px; 
    border-radius: 20px; 
    margin-bottom: 25px;
    background-image: url('data:image/png;base64,{bg_image_b64}'); 
    background-size: cover; 
    background-position: right bottom; 
    box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    overflow: hidden;
    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
">
    <div style="position: absolute; top:0; left:0; width: 60%; height: 100%; background: linear-gradient(90deg, #020617 10%, transparent 100%);"></div>
    
    <div style="position: absolute; top: 100px; left: 40px; color: white;">
        <div style="font-size: 0.85rem; font-weight: 700; letter-spacing: 2px; color: #bfdbfe; margin-bottom: 8px; text-transform: uppercase;">Odisha Government Procurement</div>
        <h1 style="font-size: 2.8rem; font-weight: 800; margin: 0; line-height: 1.1; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">
            Tender Intelligence <span style="color: #fbbf24;">Dashboard</span>
        </h1>
        <p style="color: #dbeafe; font-size: 1.1rem; margin-top: 15px; max-width: 600px;">
            Search, filter and analyze government tenders from multiple Odisha portals in one premium feed.
        </p>
        <div style="margin-top: 20px;">
            <span style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); padding: 6px 12px; border-radius: 20px; font-size: 0.8rem; margin-right: 10px;">● Live Dataset</span>
            <span style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); padding: 6px 12px; border-radius: 20px; font-size: 0.8rem; margin-right: 10px;">⚡ AI Summaries</span>
            <span style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); padding: 6px 12px; border-radius: 20px; font-size: 0.8rem;">🎯 Advanced Filtering</span>
        </div>
    </div>
</div>
"""
st.markdown(header_html.replace('\n', ' '), unsafe_allow_html=True)


# ============================================================
# KPI CARDS PLACEHOLDER
# ============================================================
kpi_container = st.empty()


# ============================================================
# FILTER BAR (Single Row + Status Filter)
# ============================================================
st.markdown("<h4 style='color: #020617; font-size: 1.15rem; font-weight: 800; margin-bottom: -5px;'>🔍 Filter Opportunities</h4>", unsafe_allow_html=True)

f1, f2, f3, f4, f5, f6, f7 = st.columns(7)

with f1:
    search_query = st.text_input("Keyword Search", placeholder="Title, ID...")
with f2:
    sources = [d for d in df["Source Portal"].dropna().unique().tolist() if str(d).strip()] if "Source Portal" in df.columns else []
    selected_sources = st.multiselect("Source Portal", options=sorted(sources), placeholder="All Portals")
with f3:
    districts = [d for d in df["District"].dropna().unique().tolist() if str(d).strip()] if "District" in df.columns else []
    selected_districts = st.multiselect("District", options=sorted(districts), placeholder="All Districts")
with f4:
    depts = [d for d in df["Department"].dropna().unique().tolist() if str(d).strip()] if "Department" in df.columns else []
    selected_depts = st.multiselect("Department", options=sorted(depts), placeholder="All Depts")
with f5:
    status_filter = st.selectbox("Status", options=["All", "Active Only", "Expired Only"])
with f6:
    selected_open_date = st.date_input("Opening (After)", value=None)
with f7:
    selected_close_date = st.date_input("Closing (Before)", value=None)


# ============================================================
# APPLY FILTERS & URGENCY LOGIC
# ============================================================
filtered_df = df.copy()
today_dt = datetime.now().date()

# Helper function to compute days left and urgency
def get_urgency_info(closing_date):
    if pd.isna(closing_date):
        return 9999, "No Closing Date", "badge-gray"
    
    delta = (closing_date.date() - today_dt).days
    
    if delta < 0:
        return delta, f"{-delta} days expired", "badge-gray"
    elif delta <= 2:
        return delta, f"{delta} days left", "badge-red"
    elif delta <= 5:
        return delta, f"{delta} days left", "badge-light-red"
    elif delta <= 7:
        return delta, f"{delta} days left", "badge-yellow"
    else:
        return delta, f"{delta} days left", "badge-green"

# Calculate Days Left & Status for all rows
filtered_df['days_left'], filtered_df['urgency_text'], filtered_df['badge_class'] = zip(*filtered_df['Closing Date'].map(get_urgency_info))
filtered_df['is_expired'] = filtered_df['days_left'] < 0

# Status Filter (Active vs Expired)
if status_filter == "Active Only":
    filtered_df = filtered_df[~filtered_df['is_expired']]
elif status_filter == "Expired Only":
    filtered_df = filtered_df[filtered_df['is_expired']]

if search_query:
    search_mask = (filtered_df["Title"].astype(str).str.contains(search_query, case=False, na=False) | filtered_df["Tender No"].astype(str).str.contains(search_query, case=False, na=False))
    if "Summary" in filtered_df.columns:
        search_mask |= filtered_df["Summary"].astype(str).str.contains(search_query, case=False, na=False)
    filtered_df = filtered_df[search_mask]

if selected_sources: filtered_df = filtered_df[filtered_df["Source Portal"].isin(selected_sources)]
if selected_districts: filtered_df = filtered_df[filtered_df["District"].isin(selected_districts)]
if selected_depts: filtered_df = filtered_df[filtered_df["Department"].isin(selected_depts)]

if selected_open_date:
    filtered_df = filtered_df[(filtered_df["Opening Date"].notna()) & (filtered_df["Opening Date"].dt.date >= selected_open_date)]

if selected_close_date:
    filtered_df = filtered_df[(filtered_df["Closing Date"].notna()) & (filtered_df["Closing Date"].dt.date <= selected_close_date)]

# SMART SORTING: Active tenders sorted by soonest closing date first. Expired pushed to bottom.
filtered_df['sort_helper'] = filtered_df['days_left'].apply(lambda x: 999999 if x < 0 else x)
filtered_df = filtered_df.sort_values(by=['sort_helper', 'Closing Date'], ascending=[True, True])


# ============================================================
# CALCULATE & RENDER KPI CARDS
# ============================================================
with kpi_container.container():
    total_tenders = len(df)
    
    # Helper to calculate active vs expired counts for any given dataframe
    def get_active_expired_counts(dataset):
        if dataset.empty: return 0, 0
        if 'days_left' in dataset.columns:
            expired_n = int((dataset['days_left'] < 0).sum())
            active_n = int((dataset['days_left'] >= 0).sum())
            return active_n, expired_n
        return 0, 0

    # Calculate counts dynamically based on current filters
    filtered_active, filtered_expired = get_active_expired_counts(filtered_df)

    dist_count = filtered_df["District"].nunique() if "District" in filtered_df.columns else 0
    total_value = filtered_df["Tender Value"].sum() if "Tender Value" in filtered_df.columns else 0

    k1, k2, k3, k4 = st.columns(4)
    
    # Total Tenders Revolving Card
    with k1: 
        st.markdown(f'''
        <div class="kpi-card kpi-blue">
            <div class="kpi-icon">📋</div>
            <div class="revolving-container">
                <div class="revolve-item item-1">
                    <div class="kpi-label">Filtered Tenders</div>
                    <div class="kpi-value">{len(filtered_df):,}</div>
                </div>
                <div class="revolve-item item-2">
                    <div class="kpi-label">Total in Database</div>
                    <div class="kpi-value">{total_tenders:,}</div>
                </div>
            </div>
        </div>
        '''.replace('\n', ' '), unsafe_allow_html=True)

    # Active & Expired Tenders Revolving Card
    with k2: 
        st.markdown(f'''
        <div class="kpi-card kpi-green">
            <div class="kpi-icon">🟢</div>
            <div class="revolving-container">
                <div class="revolve-item item-1">
                    <div class="kpi-label">Active Tenders</div>
                    <div class="kpi-value">{filtered_active:,}</div>
                </div>
                <div class="revolve-item item-2">
                    <div class="kpi-label">Expired Tenders</div>
                    <div class="kpi-value">{filtered_expired:,}</div>
                </div>
            </div>
        </div>
        '''.replace('\n', ' '), unsafe_allow_html=True)

    with k3: st.markdown(f'<div class="kpi-card kpi-orange"><div class="kpi-icon">📍</div><div class="kpi-label">Districts Covered</div><div class="kpi-value">{dist_count:,}</div></div>', unsafe_allow_html=True)
    with k4: st.markdown(f'<div class="kpi-card kpi-cyan"><div class="kpi-icon">💰</div><div class="kpi-label">Total Pipeline Value</div><div class="kpi-value">₹{total_value / 10000000:,.1f} Cr</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ============================================================
# TABS
# ============================================================
tab1, tab2 = st.tabs([f"🗂️ Tender Feed ({len(filtered_df)})", "📊 Analytics Dashboard"])

# ============================================================
# TAB 1: CARD-BASED TENDER FEED
# ============================================================
with tab1:
    if filtered_df.empty:
        st.info("No tenders match your current filters. Try adjusting your search.")
    else:
        feed_html = ""
        
        for _, row in filtered_df.iterrows():
            t_no = str(row.get('Tender No', 'N/A'))
            title = str(row.get('Title', 'Untitled Tender'))
            dept = str(row.get('Department', 'Unknown Department'))
            summary = str(row.get('Summary', 'No summary available.'))
            category = str(row.get('Category', 'General'))
            link = str(row.get('Link', '#'))
            
            dist = str(row.get('District', 'Odisha')).strip()
            addr = str(row.get('Address', '')).strip()
            if len(addr) > 85: addr = addr[:85] + "..."
            if addr == "nan" or not addr: addr = "Location details in document."
            location_text = f"<b>{dist}</b> &mdash; {addr}"
            
            val = row.get('Tender Value', 0)
            emd = row.get('EMD', 0)
            val_str = f"₹ {val:,.0f}" if val > 0 else "Refer Doc"
            emd_str = f"₹ {emd:,.0f}" if emd > 0 else "N/A"
            
            pub_d = row.get('Published Date')
            opn_d = row.get('Opening Date')
            cls_d = row.get('Closing Date')
            
            pub_str = pub_d.strftime('%d %b %Y') if pd.notnull(pub_d) else "N/A"
            opn_str = opn_d.strftime('%d %b %Y') if pd.notnull(opn_d) else "N/A"
            cls_str = cls_d.strftime('%d %b %Y') if pd.notnull(cls_d) else "N/A"
            
            urgency_text = row.get('urgency_text', '')
            badge_class = row.get('badge_class', 'badge-gray')
            
            title_html = f'<div class="tc-title">{title}</div>' if title.strip().lower() != category.strip().lower() else ''
            
            card = f"""
            <div class="tender-card">
                <div class="tc-dept-row">
                    <div class="tc-dept">{dept}</div>
                    <div class="{badge_class}">{urgency_text}</div>
                </div>
                {title_html}
                <div class="tc-meta">
                    <span class="tc-tag">🏷️ {category}</span>
                    <span style="color: #94a3b8;">|</span>
                    <span>🆔 <b>{t_no}</b></span>
                </div>
                <div class="tc-loc">📍 {location_text}</div>
                <div class="tc-summary">📝 {summary}</div>
                
                <div class="tc-grid">
                    <div><div class="tc-stat-label">Value</div><div class="tc-stat-val">💰 {val_str}</div></div>
                    <div><div class="tc-stat-label">EMD</div><div class="tc-stat-val">🛡️ {emd_str}</div></div>
                    <div><div class="tc-stat-label">Published</div><div class="tc-stat-val">📅 {pub_str}</div></div>
                    <div><div class="tc-stat-label">Opening</div><div class="tc-stat-val">🟢 {opn_str}</div></div>
                    <div><div class="tc-stat-label">Closing</div><div class="tc-stat-val">⏳ {cls_str}</div></div>
                    <div style="text-align: right;">
                        <a href="{link}" target="_blank" class="tc-btn">🔗 View Document</a>
                    </div>
                </div>
            </div>
            """
            feed_html += card.replace('\n', ' ')
            
        st.markdown(feed_html, unsafe_allow_html=True)


# ============================================================
# TAB 2: ANALYTICS
# ============================================================
with tab2:
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        if "District" in filtered_df.columns and not filtered_df.empty:
            dist_counts = filtered_df["District"].value_counts().head(10).reset_index()
            dist_counts.columns = ["District", "Tender Count"]
            fig_bar = px.bar(dist_counts, x="District", y="Tender Count", title="Top Districts by Tender Volume", template="plotly_white", text_auto=True)
            fig_bar.update_traces(marker_line_width=0, hovertemplate="<b>%{x}</b><br>Tenders: %{y}<extra></extra>")
            fig_bar.update_layout(showlegend=False, height=390, margin=dict(t=65, b=45, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_bar, use_container_width=True)

    with chart_col2:
        if "Department" in filtered_df.columns and not filtered_df.empty:
            dept_counts = filtered_df["Department"].value_counts().head(8).reset_index()
            dept_counts.columns = ["Department", "Count"]
            fig_pie = px.pie(dept_counts, values="Count", names="Department", hole=0.55, title="Department Distribution", template="plotly_white")
            fig_pie.update_traces(textposition="inside", textinfo="percent")
            fig_pie.update_layout(height=390, margin=dict(t=65, b=30, l=10, r=10), legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)

# ============================================================
# FOOTER
# ============================================================
st.markdown("<div style='text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 40px; margin-bottom: 20px;'>Tender Intelligence Platform • Shree Venkatesh Enterprises</div>", unsafe_allow_html=True)