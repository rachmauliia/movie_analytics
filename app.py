"""
Movie Analytics Dashboard
app.py — main entry point.

Routing:
  Executive Summary          → rendered inline here (Overview dashboard)
  content_performance        → pages/content_performance.py
  genre_audience             → pages/genre_audience.py
  rental_behavior            → pages/rental_behavior.py
  actor_cast                 → pages/actor_cast.py
"""

import streamlit as st
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Movie Analytics Dashboard",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎬</text></svg>",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
def load_css(path: str):
    with open(path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("styles/main.css")

# ── DB IMPORT ──────────────────────────────────────────────────────────────────
from db import run_query

# ── OVERVIEW SQL ───────────────────────────────────────────────────────────────
SQL_OV_TOTALS = """
SELECT
    COUNT(DISTINCT f.film_id)                   AS total_films,
    COUNT(DISTINCT c.customer_id)               AS total_customers,
    COUNT(r.rental_id)                          AS total_rentals,
    ROUND(COALESCE(SUM(p.amount), 0), 2)        AS total_revenue,
    COUNT(DISTINCT i.store_id)                  AS stores,
    COUNT(DISTINCT f.rating::text)              AS rating_types
FROM film f
LEFT JOIN inventory i   ON f.film_id        = i.film_id
LEFT JOIN rental r      ON i.inventory_id   = r.inventory_id
LEFT JOIN payment p     ON r.rental_id      = p.rental_id
LEFT JOIN customer c    ON r.customer_id    = c.customer_id;
"""

SQL_OV_MONTHLY = """
SELECT
    DATE_TRUNC('month', payment_date)::date AS month,
    ROUND(SUM(amount), 2)                   AS revenue
FROM payment
GROUP BY 1
ORDER BY 1;
"""

SQL_OV_TOP_FILMS = """
SELECT
    f.title,
    COUNT(r.rental_id)                          AS rental_count,
    ROUND(COALESCE(SUM(p.amount), 0), 2)        AS revenue
FROM film f
JOIN inventory i   ON f.film_id        = i.film_id
JOIN rental r      ON i.inventory_id   = r.inventory_id
LEFT JOIN payment p ON r.rental_id     = p.rental_id
GROUP BY f.title
ORDER BY revenue DESC
LIMIT 5;
"""

SQL_OV_RATING = """
SELECT
    f.rating::text                              AS rating,
    COUNT(r.rental_id)                          AS rentals,
    ROUND(COALESCE(SUM(p.amount), 0), 2)        AS revenue
FROM film f
LEFT JOIN inventory i   ON f.film_id        = i.film_id
LEFT JOIN rental r      ON i.inventory_id   = r.inventory_id
LEFT JOIN payment p     ON r.rental_id      = p.rental_id
GROUP BY f.rating
ORDER BY revenue DESC;
"""

SQL_OV_CATEGORY = """
SELECT
    c.name                                      AS category,
    COUNT(r.rental_id)                          AS rentals,
    ROUND(COALESCE(SUM(p.amount), 0), 2)        AS revenue
FROM category c
JOIN film_category fc   ON c.category_id    = fc.category_id
JOIN film f             ON fc.film_id       = f.film_id
LEFT JOIN inventory i   ON f.film_id        = i.film_id
LEFT JOIN rental r      ON i.inventory_id   = r.inventory_id
LEFT JOIN payment p     ON r.rental_id      = p.rental_id
GROUP BY c.name
ORDER BY revenue DESC
LIMIT 6;
"""

SQL_OV_DEAD = """
SELECT COUNT(*) AS dead_count
FROM film f
LEFT JOIN inventory i ON f.film_id = i.film_id
LEFT JOIN rental r    ON i.inventory_id = r.inventory_id
WHERE r.rental_id IS NULL;
"""

# ── CACHE OVERVIEW DATA ────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_overview():
    tot  = run_query(SQL_OV_TOTALS).iloc[0]
    mo   = run_query(SQL_OV_MONTHLY)
    top  = run_query(SQL_OV_TOP_FILMS)
    rat  = run_query(SQL_OV_RATING)
    cat  = run_query(SQL_OV_CATEGORY)
    dead = run_query(SQL_OV_DEAD).iloc[0]["dead_count"]
    return tot, mo, top, rat, cat, dead

# ── PLOTLY SHARED LAYOUT ───────────────────────────────────────────────────────
PL = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", size=11, color="#1a1c2e"),
    margin=dict(l=10, r=10, t=8, b=8),
)

# ── SVG ICONS ──────────────────────────────────────────────────────────────────
# Using simple inline SVGs so there are zero emoji dependencies
def icon_film(color="#6c5ce7"):
    return f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="17" y1="7" x2="22" y2="7"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="2" y1="17" x2="7" y2="17"/></svg>'

def icon_users(color="#00b894"):
    return f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>'

def icon_dollar(color="#fd9644"):
    return f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>'

def icon_cart(color="#0984e3"):
    return f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>'

def icon_warn(color="#d63031"):
    return f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'

def icon_trend(color="#6c5ce7"):
    return f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>'

def icon_star(color="#fd9644"):
    return f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>'

def icon_box(color="#00b894"):
    return f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>'

def icon_clock(color="#fd79a8"):
    return f'<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'

def icon_chart(color="#6c5ce7"):
    return f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>'

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
PAGES = {
    "Executive Summary":            "overview",
    "Content Performance":          "content_performance",
    "Genre & Audience Taste":       "genre_audience",
    "Rental Behavior & Late Return":"rental_behavior",
    "Actor & Cast Star Power":      "actor_cast",
}

with st.sidebar:
    # Brand
    st.markdown("""
        <div style="padding:1.6rem 1rem 1.2rem 1rem;border-bottom:1px solid #edeef8;">
            <div style="display:flex;align-items:center;gap:10px;">
                <div style="width:36px;height:36px;background:linear-gradient(135deg,#6c5ce7,#a29bfe);
                    border-radius:10px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff"
                        stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="2" y="2" width="20" height="20" rx="2"/>
                        <line x1="7" y1="2" x2="7" y2="22"/>
                        <line x1="17" y1="2" x2="17" y2="22"/>
                        <line x1="2" y1="12" x2="22" y2="12"/>
                    </svg>
                </div>
                <div>
                    <div style="font-size:0.95rem;font-weight:700;color:#1a1c2e;">Movie Analytics</div>
                    <div style="font-size:0.7rem;color:#9da3bd;margin-top:1px;">dvdrental &middot; PostgreSQL</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="nav-section-label" style="color:#9da3bd;font-size:0.67rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;padding:1.1rem 1rem 0.4rem 1rem;">Main Menu</div>', unsafe_allow_html=True)

    page = st.radio(
        label="navigation",
        options=list(PAGES.keys()),
        label_visibility="collapsed",
    )

    st.markdown("""
        <div style="margin:1.5rem 1rem 0 1rem;background:rgba(108,92,231,0.07);
            border:1px solid rgba(108,92,231,0.15);border-radius:10px;
            padding:0.8rem 1rem;font-size:0.75rem;color:#6c5ce7;line-height:1.55;">
            <span style="font-weight:600;">Tip</span><br>
            <span style="color:#8a8fa8;">Use the sidebar filters on each feature page to drill into specific data.</span>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <p style="font-size:0.67rem;color:#c0c4d8;text-align:center;margin-top:2rem;padding:0 1rem;">
            Movie Analytics Dashboard &nbsp;&middot;&nbsp; v1.0
        </p>
    """, unsafe_allow_html=True)


# ── ROUTING ────────────────────────────────────────────────────────────────────
page_key = PAGES[page]

if page_key == "content_performance":
    from pages.content_performance import render
    render()

elif page_key == "genre_audience":
    from pages.genre_audience import render
    render()

elif page_key == "rental_behavior":
    from pages.rental_behavior import render
    render()

elif page_key == "actor_cast":
    from pages.actor_cast import render
    render()

else:
    # ═══════════════════════════════════════════════════════════════════════════
    # OVERVIEW DASHBOARD
    # ═══════════════════════════════════════════════════════════════════════════

    with st.spinner("Loading overview data..."):
        tot, df_mo, df_top, df_rat, df_cat, dead_count = load_overview()

    today_str = date.today().strftime("%A, %B %d, %Y")

    # ── Top bar ────────────────────────────────────────────────────────────────
    st.markdown(f"""
        <div class="ov-topbar">
            <div>
                <div class="ov-title">Executive Summary</div>
                <div class="ov-sub">Movie rental performance at a glance</div>
            </div>
            <div class="ov-date-chip">{today_str}</div>
        </div>
    """, unsafe_allow_html=True)

    # ── Row 1: 4 colored summary cards ────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
            <div class="sc-card purple">
                <div class="sc-label">Total Revenue</div>
                <div class="sc-value">${tot['total_revenue']:,.0f}</div>
                <div class="sc-sub">All-time payment income</div>
                <div class="sc-wm">$</div>
            </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
            <div class="sc-card teal">
                <div class="sc-label">Total Rentals</div>
                <div class="sc-value">{int(tot['total_rentals']):,}</div>
                <div class="sc-sub">Total transactions</div>
                <div class="sc-wm">#</div>
            </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
            <div class="sc-card orange">
                <div class="sc-label">Film Catalog</div>
                <div class="sc-value">{int(tot['total_films']):,}</div>
                <div class="sc-sub">Unique titles in inventory</div>
                <div class="sc-wm">F</div>
            </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
            <div class="sc-card blue">
                <div class="sc-label">Active Customers</div>
                <div class="sc-value">{int(tot['total_customers']):,}</div>
                <div class="sc-sub">Customers who rented</div>
                <div class="sc-wm">C</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

    # ── Row 2: KPI detail cards ────────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)
    avg_rev_per_rental = float(tot['total_revenue']) / max(int(tot['total_rentals']), 1)
    with k1:
        st.markdown(f"""
            <div class="kpi-card purple">
                <div class="kpi-icon-box purple">{icon_trend('#6c5ce7')}</div>
                <div class="kpi-label">Avg Revenue / Rental</div>
                <div class="kpi-value">${avg_rev_per_rental:.2f}</div>
                <div class="kpi-sub">Based on {int(tot['total_rentals']):,} rentals</div>
            </div>
        """, unsafe_allow_html=True)
    with k2:
        avg_rev_per_film = float(tot['total_revenue']) / max(int(tot['total_films']), 1)
        st.markdown(f"""
            <div class="kpi-card teal">
                <div class="kpi-icon-box teal">{icon_film('#00b894')}</div>
                <div class="kpi-label">Avg Revenue / Film</div>
                <div class="kpi-value">${avg_rev_per_film:.2f}</div>
                <div class="kpi-sub">Across {int(tot['total_films']):,} titles</div>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
            <div class="kpi-card red">
                <div class="kpi-icon-box red">{icon_warn('#d63031')}</div>
                <div class="kpi-label">Dead Stock Films</div>
                <div class="kpi-value">{int(dead_count)}</div>
                <div class="kpi-sub">Films with zero rentals</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # ── Row 3: Revenue trend + Top films + Rating breakdown ───────────────────
    col_main, col_side = st.columns([2, 1])

    with col_main:
        # Monthly revenue trend
        st.markdown('<div class="white-card">', unsafe_allow_html=True)
        st.markdown('<div class="white-card-title">Monthly Revenue Trend</div>', unsafe_allow_html=True)
        st.markdown('<div class="white-card-sub">Total payment income per month across all rentals</div>', unsafe_allow_html=True)

        fig_mo = go.Figure()
        fig_mo.add_trace(go.Scatter(
            x=df_mo["month"], y=df_mo["revenue"],
            mode="lines+markers",
            fill="tozeroy",
            line=dict(color="#6c5ce7", width=2.5),
            fillcolor="rgba(108,92,231,0.08)",
            marker=dict(size=5, color="#6c5ce7"),
            hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.2f}<extra></extra>",
        ))
        fig_mo.update_layout(
            **PL,
            height=220,
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=True, gridcolor="#f0f1f8", zeroline=False),
        )
        st.plotly_chart(fig_mo, width='stretch', config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col_side:
        # Top 5 films milestone list
        st.markdown('<div class="white-card" style="height:100%;box-sizing:border-box;">', unsafe_allow_html=True)
        st.markdown('<div class="white-card-title">Top 5 Films by Revenue</div>', unsafe_allow_html=True)
        st.markdown('<div class="white-card-sub">Highest earning titles</div>', unsafe_allow_html=True)

        max_rev = df_top["revenue"].max() if not df_top.empty else 1
        dot_colors = ["#6c5ce7", "#00b894", "#fd9644", "#0984e3", "#fd79a8"]

        for i, row in df_top.iterrows():
            pct = int(row["revenue"] / max_rev * 100)
            color = dot_colors[i % len(dot_colors)]
            st.markdown(f"""
                <div class="ms-row">
                    <div class="ms-dot" style="background:{color};"></div>
                    <div>
                        <div class="ms-text" style="font-size:0.78rem;">{row['title']}</div>
                        <div class="ms-sub">{int(row['rental_count'])} rentals</div>
                    </div>
                    <div class="ms-bar-wrap">
                        <div class="ms-bar" style="width:{pct}%;background:{color};"></div>
                    </div>
                    <div class="ms-pct" style="color:{color};">${row['revenue']:,.0f}</div>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    # ── Row 4: Rating donut + Category bar + Genre milestone ──────────────────
    col_a, col_b = st.columns([1, 1])

    with col_a:
        st.markdown('<div class="white-card">', unsafe_allow_html=True)
        st.markdown('<div class="white-card-title">Revenue by Rating</div>', unsafe_allow_html=True)
        st.markdown('<div class="white-card-sub">Which rating tier generates the most income</div>', unsafe_allow_html=True)

        rating_colors_map = {
            "G": "#1e8449", "PG": "#1a5276", "PG-13": "#d68910",
            "R": "#c0392b", "NC-17": "#6c3483",
        }
        fig_rat = px.pie(
            df_rat, names="rating", values="revenue",
            color="rating", color_discrete_map=rating_colors_map,
            hole=0.55,
        )
        fig_rat.update_traces(
            textposition="outside", textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<extra></extra>",
        )
        fig_rat.update_layout(**PL, height=240, showlegend=False)
        st.plotly_chart(fig_rat, width='stretch', config={"displayModeBar": False})

        # Rating legend with short descriptions
        st.markdown("""
            <div style="margin-top:0.5rem;padding:0.65rem 0.85rem;background:#f8f9fc;border-radius:8px;border:1px solid #edeef8;">
                <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:#9da3bd;margin-bottom:0.45rem;">Rating Guide</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.3rem 1rem;">
                    <div style="display:flex;align-items:center;gap:0.4rem;">
                        <span style="width:10px;height:10px;border-radius:50%;background:#1e8449;flex-shrink:0;"></span>
                        <span style="font-size:0.72rem;color:#374151;"><strong>G</strong> — All ages</span>
                    </div>
                    <div style="display:flex;align-items:center;gap:0.4rem;">
                        <span style="width:10px;height:10px;border-radius:50%;background:#1a5276;flex-shrink:0;"></span>
                        <span style="font-size:0.72rem;color:#374151;"><strong>PG</strong> — Parental guidance</span>
                    </div>
                    <div style="display:flex;align-items:center;gap:0.4rem;">
                        <span style="width:10px;height:10px;border-radius:50%;background:#d68910;flex-shrink:0;"></span>
                        <span style="font-size:0.72rem;color:#374151;"><strong>PG-13</strong> — 13 years and above</span>
                    </div>
                    <div style="display:flex;align-items:center;gap:0.4rem;">
                        <span style="width:10px;height:10px;border-radius:50%;background:#c0392b;flex-shrink:0;"></span>
                        <span style="font-size:0.72rem;color:#374151;"><strong>R</strong> — 17 years and above</span>
                    </div>
                    <div style="display:flex;align-items:center;gap:0.4rem;">
                        <span style="width:10px;height:10px;border-radius:50%;background:#6c3483;flex-shrink:0;"></span>
                        <span style="font-size:0.72rem;color:#374151;"><strong>NC-17</strong> — 18 years and above</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="white-card">', unsafe_allow_html=True)
        st.markdown('<div class="white-card-title">Top Genres by Revenue</div>', unsafe_allow_html=True)
        st.markdown('<div class="white-card-sub">Revenue contribution from the top 6 categories</div>', unsafe_allow_html=True)

        genre_colors = ["#6c5ce7","#00b894","#fd9644","#0984e3","#fd79a8","#a29bfe"]
        max_cat = df_cat["revenue"].max() if not df_cat.empty else 1
        for i, row in df_cat.iterrows():
            pct = int(row["revenue"] / max_cat * 100)
            color = genre_colors[i % len(genre_colors)]
            st.markdown(f"""
                <div class="ms-row">
                    <div class="ms-dot" style="background:{color};"></div>
                    <div style="flex:1;min-width:0;">
                        <div class="ms-text">{row['category']}</div>
                        <div class="ms-sub">{int(row['rentals'])} rentals</div>
                    </div>
                    <div class="ms-bar-wrap" style="width:80px;">
                        <div class="ms-bar" style="width:{pct}%;background:{color};"></div>
                    </div>
                    <div class="ms-pct" style="color:{color};">${row['revenue']:,.0f}</div>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

    # ── Row 5: Feature shortcuts ───────────────────────────────────────────────
    st.markdown('<div class="section-title">Explore Features</div>', unsafe_allow_html=True)

    f1, f2, f3, f4 = st.columns(4)
    features = [
        {
            "col": f1, "color": "purple",
            "svg": icon_chart('#6c5ce7'),
            "title": "Content Performance",
            "desc": "Top & bottom films, ROI analysis, dead stock, and rating profitability.",
            "status": "live",
        },
        {
            "col": f2, "color": "teal",
            "svg": icon_star('#00b894'),
            "title": "Genre & Audience Taste",
            "desc": "Which genres drive rentals, audience preferences by rating and category.",
            "status": "live",
        },
        {
            "col": f3, "color": "orange",
            "svg": icon_clock('#fd9644'),
            "title": "Rental Behavior",
            "desc": "Late returns, peak rental periods, rental duration patterns and trends.",
            "status": "live",
        },
        {
            "col": f4, "color": "pink",
            "svg": icon_star('#fd79a8'),
            "title": "Actor & Cast Power",
            "desc": "Which actors and casts drive the most rentals and revenue.",
            "status": "live",
        },
    ]

    for feat in features:
        with feat["col"]:
            st.markdown(f"""
                <div class="fc-card">
                    <div class="fc-icon {feat['color']}">{feat['svg']}</div>
                    <div class="fc-title">{feat['title']}</div>
                    <div class="fc-desc">{feat['desc']}</div>
                    <span class="fc-badge {feat['status']}">
                        {'Available' if feat['status'] == 'live' else 'Coming Soon'}
                    </span>
                </div>
            """, unsafe_allow_html=True)