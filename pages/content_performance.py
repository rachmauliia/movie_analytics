"""
Feature 1 — Content Performance & Revenue Intelligence
"Which films are making money, and which are just taking up space?"
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.cards import kpi_card, page_header, section_title
from db import run_query

# ── PALETTE ────────────────────────────────────────────────────────────────────
RATING_COLORS = {
    "G":     "#1e8449",
    "PG":    "#1a5276",
    "PG-13": "#d68910",
    "R":     "#c0392b",
    "NC-17": "#6c3483",
}
PURPLE = "#6c5ce7"
TEAL   = "#00b894"
ORANGE = "#fd9644"
PINK   = "#fd79a8"
BLUE   = "#0984e3"

PL = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", size=11, color="#1a1c2e"),
    margin=dict(l=10, r=10, t=24, b=10),
    legend=dict(
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#edeef8",
        borderwidth=1,
        font=dict(size=10),
    ),
)

# ── SQL ────────────────────────────────────────────────────────────────────────
SQL_FILM = """
SELECT
    f.film_id,
    f.title,
    f.rating::text                              AS rating,
    f.rental_rate,
    f.replacement_cost,
    COUNT(r.rental_id)                          AS rental_count,
    COALESCE(SUM(p.amount), 0)                  AS total_revenue,
    ROUND(
        COALESCE(SUM(p.amount),0)
        / NULLIF(f.replacement_cost,0)*100, 2
    )                                           AS roi_pct
FROM film f
LEFT JOIN inventory i   ON f.film_id        = i.film_id
LEFT JOIN rental r      ON i.inventory_id   = r.inventory_id
LEFT JOIN payment p     ON r.rental_id      = p.rental_id
GROUP BY f.film_id, f.title, f.rating, f.rental_rate, f.replacement_cost
ORDER BY total_revenue DESC;
"""

SQL_RATING = """
SELECT
    f.rating::text                              AS rating,
    COUNT(DISTINCT f.film_id)                   AS film_count,
    COUNT(r.rental_id)                          AS rental_count,
    ROUND(COALESCE(SUM(p.amount),0),2)          AS total_revenue,
    ROUND(AVG(p.amount),2)                      AS avg_payment,
    ROUND(
        COALESCE(SUM(p.amount),0)
        / NULLIF(COUNT(DISTINCT f.film_id),0),2
    )                                           AS revenue_per_film
FROM film f
LEFT JOIN inventory i   ON f.film_id        = i.film_id
LEFT JOIN rental r      ON i.inventory_id   = r.inventory_id
LEFT JOIN payment p     ON r.rental_id      = p.rental_id
GROUP BY f.rating
ORDER BY total_revenue DESC;
"""

SQL_MONTHLY = """
SELECT
    DATE_TRUNC('month', p.payment_date)::date   AS month,
    f.rating::text                              AS rating,
    ROUND(SUM(p.amount),2)                      AS revenue
FROM payment p
JOIN rental r     ON p.rental_id      = r.rental_id
JOIN inventory i  ON r.inventory_id   = i.inventory_id
JOIN film f       ON i.film_id        = f.film_id
GROUP BY 1,2
ORDER BY 1,2;
"""

SQL_CATEGORY = """
SELECT
    c.name                                      AS category,
    COUNT(r.rental_id)                          AS rental_count,
    ROUND(COALESCE(SUM(p.amount),0),2)          AS total_revenue,
    COUNT(DISTINCT f.film_id)                   AS film_count,
    ROUND(
        COALESCE(SUM(p.amount),0)
        / NULLIF(COUNT(DISTINCT f.film_id),0),2
    )                                           AS revenue_per_film
FROM category c
JOIN film_category fc   ON c.category_id    = fc.category_id
JOIN film f             ON fc.film_id       = f.film_id
LEFT JOIN inventory i   ON f.film_id        = i.film_id
LEFT JOIN rental r      ON i.inventory_id   = r.inventory_id
LEFT JOIN payment p     ON r.rental_id      = p.rental_id
GROUP BY c.name
ORDER BY total_revenue DESC;
"""

# ── CSS ────────────────────────────────────────────────────────────────────────
CARD_CSS = """
<style>
.insight-panel {
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin: 0.6rem 0 1rem 0;
    font-size: 0.84rem;
    line-height: 1.75;
    color: #1a1c2e;
}
.insight-panel ul {
    margin: 0.35rem 0 0 0;
    padding-left: 1.2rem;
}
.insight-panel li { margin-bottom: 0.3rem; }
.panel-positive {
    background: #f0fdf4;
    border-left: 4px solid #16a34a;
    border: 1px solid #bbf7d0;
    border-left: 4px solid #16a34a;
}
.panel-negative {
    background: #fff5f5;
    border: 1px solid #fecaca;
    border-left: 4px solid #dc2626;
}
.panel-action {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-left: 4px solid #2563eb;
}
.panel-title {
    font-weight: 700;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
}
.chart-desc {
    font-size: 0.78rem;
    color: #6b7280;
    margin: 0 0 0.75rem 0;
    font-style: italic;
    line-height: 1.5;
    padding: 0.5rem 0.75rem;
    background: #f8f9fc;
    border-radius: 6px;
    border-left: 3px solid #e0e2ef;
}
.dead-badge {
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #b91c1c;
    padding: 0.4rem 0.9rem;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.84rem;
    display: inline-block;
}
.slow-badge {
    background: #fffbeb;
    border: 1px solid #fde68a;
    color: #92400e;
    padding: 0.4rem 0.9rem;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.84rem;
    display: inline-block;
}
</style>
"""


def _panel(cls, title_color, title_text, items):
    li_html = "".join(f"<li>{i}</li>" for i in items)
    st.markdown(
        f'<div class="insight-panel {cls}">'
        f'<div class="panel-title" style="color:{title_color};">{title_text}</div>'
        f"<ul>{li_html}</ul></div>",
        unsafe_allow_html=True,
    )


def chart_desc(text):
    st.markdown(f'<p class="chart-desc">{text}</p>', unsafe_allow_html=True)


# ── DATA ───────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_all():
    return (
        run_query(SQL_FILM),
        run_query(SQL_RATING),
        run_query(SQL_MONTHLY),
        run_query(SQL_CATEGORY),
    )


# ── CHARTS ────────────────────────────────────────────────────────────────────
def fig_top_bar(df, n, ascending=False):
    if ascending:
        data   = df[df["rental_count"] > 0].nsmallest(n, "total_revenue")
        colors = [PINK, "#d63031"]
    else:
        data   = df.nlargest(n, "total_revenue")
        colors = [PURPLE, "#a29bfe"]

    fig = px.bar(
        data, x="total_revenue", y="title", orientation="h",
        color="total_revenue",
        color_continuous_scale=colors,
        hover_data=["rating", "rental_count"],
        labels={"total_revenue": "Revenue ($)", "title": "Film"},
    )
    fig.update_layout(
        **PL, height=max(300, n * 36),
        yaxis=dict(autorange="reversed"),
        showlegend=False, coloraxis_showscale=False,
    )
    return fig


def fig_roi_scatter(df):
    d   = df[df["rental_count"] > 0].copy()
    fig = px.scatter(
        d, x="replacement_cost", y="total_revenue",
        color="rating", size="rental_count",
        hover_name="title",
        color_discrete_map=RATING_COLORS,
        size_max=28,
        labels={
            "replacement_cost": "Replacement Cost ($)",
            "total_revenue":    "Total Revenue ($)",
            "rental_count":     "Rentals",
        },
    )
    mx = max(d["replacement_cost"].max(), d["total_revenue"].max())
    fig.add_shape(type="line", x0=0, y0=0, x1=mx, y1=mx,
                  line=dict(color="#b2bec3", width=1.5, dash="dash"))
    fig.add_annotation(x=mx * 0.82, y=mx * 0.95, text="Break-even line",
                       showarrow=False, font=dict(size=10, color="#b2bec3"))
    fig.update_layout(**PL, height=420)
    return fig


def fig_rating_combo(df_r):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Total Revenue", x=df_r["rating"], y=df_r["total_revenue"],
        marker_color=PURPLE, yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        name="Revenue / Film", x=df_r["rating"], y=df_r["revenue_per_film"],
        mode="lines+markers",
        marker=dict(size=8, color=ORANGE),
        line=dict(width=2.5, color=ORANGE),
        yaxis="y2",
    ))
    fig.update_layout(
        **PL, height=340,
        yaxis=dict(title="Total Revenue ($)", gridcolor="#f0f1f8"),
        yaxis2=dict(title="Revenue / Film ($)", overlaying="y", side="right"),
        xaxis_title="Rating",
    )
    return fig


def fig_rating_donut(df_r):
    fig = px.pie(
        df_r, names="rating", values="total_revenue",
        color="rating", color_discrete_map=RATING_COLORS, hole=0.55,
    )
    fig.update_traces(
        textposition="outside", textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<extra></extra>",
    )
    fig.update_layout(**PL, height=300, showlegend=False)
    return fig


def fig_monthly_area(df_m):
    fig = px.area(
        df_m, x="month", y="revenue", color="rating",
        color_discrete_map=RATING_COLORS,
        labels={"month": "Month", "revenue": "Revenue ($)"},
    )
    fig.update_layout(**PL, height=320, yaxis=dict(gridcolor="#f0f1f8"))
    return fig


def fig_category_hbar(df_c):
    fig = px.bar(
        df_c.sort_values("total_revenue"),
        x="total_revenue", y="category", orientation="h",
        color="revenue_per_film",
        color_continuous_scale=["#a29bfe", PURPLE, "#2d3436"],
        labels={
            "total_revenue":    "Total Revenue ($)",
            "category":         "Genre",
            "revenue_per_film": "Revenue / Film ($)",
        },
        hover_data=["rental_count", "film_count"],
    )
    fig.update_layout(
        **PL, height=460,
        coloraxis_colorbar=dict(title="$/Film", thickness=12),
    )
    return fig


def fig_roi_top(df, n):
    d   = df[df["rental_count"] > 0].nlargest(n, "roi_pct")
    fig = px.bar(
        d, x="roi_pct", y="title", orientation="h",
        color="rating", color_discrete_map=RATING_COLORS,
        labels={"roi_pct": "ROI (%)", "title": "Film"},
        hover_data=["total_revenue", "replacement_cost", "rental_count"],
    )
    fig.update_layout(**PL, height=max(300, n * 30), yaxis=dict(autorange="reversed"))
    return fig


def fig_genre_bubble(df_c):
    fig = px.scatter(
        df_c, x="rental_count", y="total_revenue",
        size="film_count", text="category",
        color="revenue_per_film",
        color_continuous_scale=["#a29bfe", PURPLE],
        labels={
            "rental_count":     "Total Rentals",
            "total_revenue":    "Total Revenue ($)",
            "film_count":       "Films",
            "revenue_per_film": "Rev/Film ($)",
        },
        size_max=42,
    )
    fig.update_traces(textposition="top center", textfont_size=10)
    fig.update_layout(**PL, height=360)
    return fig


# ── INSIGHT PANELS ─────────────────────────────────────────────────────────────
def inline_insights(df, df_rating, df_cat):
    active_df      = df[df["rental_count"] > 0]
    dead_count     = int((df["rental_count"] == 0).sum())
    dead_cost      = df[df["rental_count"] == 0]["replacement_cost"].sum()
    top1           = df.nlargest(1, "total_revenue").iloc[0]
    top3_films     = df.nlargest(3, "total_revenue")["title"].tolist()
    top_roi_film   = active_df.nlargest(1, "roi_pct").iloc[0]
    best_rating    = df_rating.loc[df_rating["revenue_per_film"].idxmax(), "rating"]
    best_rpf       = df_rating.loc[df_rating["revenue_per_film"].idxmax(), "revenue_per_film"]
    top_genre      = df_cat.nlargest(1, "total_revenue").iloc[0]
    top_genre_rpf  = df_cat.nlargest(1, "revenue_per_film").iloc[0]
    slow_films     = int(((df["rental_count"] > 0) & (df["rental_count"] <= 2)).sum())
    low_roi_count  = int((active_df["roi_pct"] < 100).sum())

    _panel("panel-positive", "#15803d", "Positive Findings", [
        f"Top earning film: <strong>{top1['title']}</strong> — ${top1['total_revenue']:,.2f} from {int(top1['rental_count'])} rentals.",
        f"Top 3 films by revenue: <strong>{', '.join(top3_films)}</strong>. Ensure these titles are always in stock.",
        f"Highest ROI film: <strong>{top_roi_film['title']}</strong> — {top_roi_film['roi_pct']:.1f}% ROI. Already well beyond break-even.",
        f"Most profitable rating per film: <strong>{best_rating}</strong> at ${best_rpf:,.2f}/film average. Prioritize stocking this rating.",
        f"Best-grossing genre: <strong>{top_genre['category']}</strong> (${top_genre['total_revenue']:,.2f} total) — proven audience demand.",
        f"Most efficient genre (revenue/film): <strong>{top_genre_rpf['category']}</strong> at ${top_genre_rpf['revenue_per_film']:,.2f}/film.",
    ])

    _panel("panel-negative", "#b91c1c", "Areas of Concern", [
        f"<strong>{dead_count} films have never been rented</strong> — ${dead_cost:,.2f} in replacement cost tied up with zero return.",
        f"<strong>{slow_films} films rented only 1-2 times</strong> — very low performance, at risk of becoming dead stock.",
        f"<strong>{low_roi_count} active films</strong> have not recovered their replacement cost (ROI below 100%).",
        "Revenue is highly concentrated in a small number of films — portfolio diversification should be considered.",
    ])

    _panel("panel-action", "#1d4ed8", "Recommended Actions", [
        f"<strong>New Stock Priority:</strong> Focus on {top_genre_rpf['category']} genre and {best_rating} rating — this combination shows the highest ROI historically.",
        f"<strong>Promote Dead Stock:</strong> Run a targeted discount or bundle campaign for the {dead_count} unrented films.",
        f"<strong>Rotate Slow Movers:</strong> Replace the {slow_films} titles with 1-2 rentals using proven genre/rating combinations.",
        f"<strong>Feature Top Performers:</strong> Display <strong>{top3_films[0]}</strong> and <strong>{top3_films[1]}</strong> prominently on the homepage or storefront.",
        "<strong>Quarterly Review:</strong> Repeat this analysis every quarter — content trends shift, and dead stock accumulates without regular monitoring.",
    ])


# ── DEAD STOCK ─────────────────────────────────────────────────────────────────
def dead_stock_section(df):
    section_title("warn", "Dead Stock — Films Never or Rarely Rented", "red")
    never = df[df["rental_count"] == 0].copy()
    slow  = df[(df["rental_count"] > 0) & (df["rental_count"] <= 2)].copy()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f'<div class="dead-badge">Never Rented: {len(never)} films</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="slow-badge">Rented 1-2x: {len(slow)} films</div>',
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    tabs = st.tabs(["Never Rented", "Rented 1-2x"])
    with tabs[0]:
        if never.empty:
            st.success("Every film has been rented at least once.")
        else:
            d          = never[["title", "rating", "rental_rate", "replacement_cost"]].copy()
            d.columns  = ["Title", "Rating", "Rental Rate ($)", "Replacement Cost ($)"]
            st.dataframe(d.reset_index(drop=True), use_container_width=True)
    with tabs[1]:
        if slow.empty:
            st.success("No films with 1-2 rentals found.")
        else:
            d          = slow[["title", "rating", "rental_count", "total_revenue", "replacement_cost"]].copy()
            d.columns  = ["Title", "Rating", "Rentals", "Revenue ($)", "Replacement Cost ($)"]
            st.dataframe(d.reset_index(drop=True), use_container_width=True)


# ── MAIN ──────────────────────────────────────────────────────────────────────
def render():
    st.markdown(CARD_CSS, unsafe_allow_html=True)

    page_header(
        "Content Performance & Revenue Intelligence",
        "Which films are making money — and which are just taking up space?",
        "Feature 1",
    )

    with st.spinner("Loading data..."):
        df_film, df_rating, df_monthly, df_cat = load_all()

    # Sidebar filters
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        '<p style="font-size:0.7rem;font-weight:600;text-transform:uppercase;'
        'letter-spacing:0.08em;color:#9da3bd;margin-bottom:0.4rem;">Filters</p>',
        unsafe_allow_html=True,
    )
    all_ratings = sorted(df_film["rating"].dropna().unique().tolist())
    sel_ratings = st.sidebar.multiselect("Rating", all_ratings, default=all_ratings, key="cp_r")
    min_rent    = st.sidebar.slider("Min Rentals", 0, int(df_film["rental_count"].max()), 0, key="cp_mr")
    top_n       = st.sidebar.select_slider("Top / Bottom N", [5, 10, 15, 20], value=10, key="cp_n")

    df = df_film.copy()
    if sel_ratings:
        df = df[df["rating"].isin(sel_ratings)]
    df = df[df["rental_count"] >= min_rent]

    if df.empty:
        st.warning("No data matches current filters.")
        return

    # ── KPI row ───────────────────────────────────────────────────────────────
    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("Total Revenue",  f"${df['total_revenue'].sum():,.0f}",  "All filtered films",         "purple", "dollar")
    with c2:
        kpi_card("Total Rentals",  f"{int(df['rental_count'].sum()):,}",  "Across active films",        "teal",   "film")
    with c3:
        kpi_card("Active Films",   f"{int((df['rental_count']>0).sum()):,}", "Films with 1+ rental",   "blue",   "check")
    with c4:
        avg_roi = df[df["rental_count"] > 0]["roi_pct"].mean()
        kpi_card("Avg ROI",        f"{avg_roi:.1f}%",                     "Revenue / replacement cost", "orange", "trend")
    with c5:
        dead = int((df["rental_count"] == 0).sum())
        kpi_card("Dead Stock",     str(dead),                             "Films never rented",         "red",    "warn")

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "Top & Bottom Films",
        "ROI Analysis",
        "Rating & Genre",
    ])

    # ── Tab 1 ─────────────────────────────────────────────────────────────────
    with tab1:
        section_title("bar", f"Top {top_n} & Bottom {top_n} Films by Revenue")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="white-card"><div class="white-card-title">Top Films</div><div class="white-card-sub">Highest earning titles</div>', unsafe_allow_html=True)
            chart_desc("Horizontal bar chart showing the highest-revenue films. Color intensity reflects revenue magnitude — darker bars indicate higher earnings.")
            st.plotly_chart(fig_top_bar(df, top_n, ascending=False), use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)
            with st.expander(f"View Top {top_n} Films — Detail Table", expanded=False):
                tdf            = df.nlargest(top_n, "total_revenue")[["title", "rating", "rental_count", "total_revenue"]].reset_index(drop=True)
                tdf.index     += 1
                tdf.columns    = ["Title", "Rating", "Rentals", "Revenue ($)"]
                tdf["Revenue ($)"] = tdf["Revenue ($)"].map("${:,.2f}".format)
                st.dataframe(tdf, use_container_width=True)

        with col2:
            st.markdown('<div class="white-card"><div class="white-card-title">Bottom Films</div><div class="white-card-sub">Lowest earning titles with at least 1 rental</div>', unsafe_allow_html=True)
            chart_desc("Films with the weakest revenue performance — all have been rented at least once but generate minimal income. These are candidates for repricing or removal.")
            st.plotly_chart(fig_top_bar(df, top_n, ascending=True), use_container_width=True, config={"displayModeBar": False})
            st.markdown('</div>', unsafe_allow_html=True)
            with st.expander(f"View Bottom {top_n} Films — Detail Table", expanded=False):
                bdf            = df[df["rental_count"] > 0].nsmallest(top_n, "total_revenue")[["title", "rating", "rental_count", "total_revenue"]].reset_index(drop=True)
                bdf.index     += 1
                bdf.columns    = ["Title", "Rating", "Rentals", "Revenue ($)"]
                bdf["Revenue ($)"] = bdf["Revenue ($)"].map("${:,.2f}".format)
                st.dataframe(bdf, use_container_width=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        dead_stock_section(df)

    # ── Tab 2 ─────────────────────────────────────────────────────────────────
    with tab2:
        section_title("trend", "ROI — Revenue vs Replacement Cost")
        chart_desc("Each dot represents one film. Films above the dashed break-even line have recovered their replacement cost through rental revenue. Bubble size indicates total rental volume — larger bubbles mean more rentals.")
        st.plotly_chart(fig_roi_scatter(df), use_container_width=True, config={"displayModeBar": False})

        # Inline insight
        above_be = int((df[df["rental_count"] > 0]["roi_pct"] >= 100).sum())
        below_be = int((df[df["rental_count"] > 0]["roi_pct"] < 100).sum())
        _panel("panel-positive", "#15803d", "What This Chart Tells Us", [
            f"<strong>{above_be} films</strong> have already exceeded their replacement cost — these titles are generating pure profit.",
            f"<strong>{below_be} active films</strong> are still below break-even — rental income has not yet covered acquisition cost.",
            "Films clustered well above the line are your most capital-efficient assets. Prioritize keeping them in stock.",
        ])

        section_title("star", f"Top {top_n} Films by ROI %")
        chart_desc("Ranks films by return on investment percentage — how many times over a film has recouped its replacement cost through rental revenue. Color indicates rating category.")
        st.plotly_chart(fig_roi_top(df, top_n), use_container_width=True, config={"displayModeBar": False})

        with st.expander(f"View Top {top_n} Films by ROI — Detail Table", expanded=False):
            rt         = df[df["rental_count"] > 0].nlargest(top_n, "roi_pct")[
                ["title", "rating", "rental_count", "total_revenue", "replacement_cost", "roi_pct"]
            ].reset_index(drop=True)
            rt.index  += 1
            rt.columns = ["Title", "Rating", "Rentals", "Revenue ($)", "Replace. Cost ($)", "ROI (%)"]
            rt["Revenue ($)"]       = rt["Revenue ($)"].map("${:,.2f}".format)
            rt["Replace. Cost ($)"] = rt["Replace. Cost ($)"].map("${:,.2f}".format)
            rt["ROI (%)"]           = rt["ROI (%)"].map("{:.1f}%".format)
            st.dataframe(rt, use_container_width=True)

    # ── Tab 3 ─────────────────────────────────────────────────────────────────
    with tab3:
        section_title("tag", "Revenue & Profitability by Rating")
        c1, c2 = st.columns([3, 2])
        with c1:
            chart_desc("Bars (left axis) show total revenue per rating category. The orange line (right axis) shows revenue per film — a measure of how efficient each rating is as an investment. A higher line means each title in that rating earns more on average.")
            st.plotly_chart(fig_rating_combo(df_rating), use_container_width=True, config={"displayModeBar": False})
        with c2:
            chart_desc("Revenue share breakdown by rating. Shows which rating classifications contribute most to overall income.")
            st.plotly_chart(fig_rating_donut(df_rating), use_container_width=True, config={"displayModeBar": False})

        best = df_rating.loc[df_rating["revenue_per_film"].idxmax(), "rating"]
        _panel("panel-action", "#1d4ed8", "Rating Insight", [
            f"Most profitable rating per film: <strong>{best}</strong> — highest average revenue per title.",
            "Stocking more films of this rating yields the best return per unit of inventory investment.",
        ])

        section_title("bar", "Monthly Revenue Trend by Rating")
        df_mf = df_monthly[df_monthly["rating"].isin(sel_ratings)]
        chart_desc("Stacked area chart showing how revenue from each rating category has trended month by month. The total height of the stack at any point represents combined revenue across all ratings. Useful for spotting seasonal patterns or shifts in audience preference.")
        st.plotly_chart(fig_monthly_area(df_mf), use_container_width=True, config={"displayModeBar": False})

        section_title("box", "Rating Summary Table")
        with st.expander("View Rating Summary — Detail Table", expanded=True):
            rt2         = df_rating.copy()
            rt2.columns = ["Rating", "Films", "Rentals", "Total Revenue ($)", "Avg Payment ($)", "Revenue / Film ($)"]
            rt2["Total Revenue ($)"]  = rt2["Total Revenue ($)"].map("${:,.2f}".format)
            rt2["Avg Payment ($)"]    = rt2["Avg Payment ($)"].map("${:,.2f}".format)
            rt2["Revenue / Film ($)"] = rt2["Revenue / Film ($)"].map("${:,.2f}".format)
            st.dataframe(rt2.reset_index(drop=True), use_container_width=True)

        st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
        section_title("box", "Revenue by Genre")
        chart_desc("Horizontal bar chart comparing total revenue across all genres. Bar length reflects total revenue earned — longer bars mean more income. Color intensity (light to dark) reflects revenue per film: darker bars indicate more efficient genres where each title generates higher returns.")
        st.plotly_chart(fig_category_hbar(df_cat), use_container_width=True, config={"displayModeBar": False})

        c1, c2 = st.columns(2)
        with c1:
            section_title("bar", "Genre Rentals vs Revenue Bubble")
            chart_desc("Bubble chart comparing rental volume (x-axis) against revenue (y-axis) per genre. Bubble size represents number of films in that genre — larger bubbles mean more titles. Color intensity reflects revenue per film.")
            st.plotly_chart(fig_genre_bubble(df_cat), use_container_width=True, config={"displayModeBar": False})
        with c2:
            section_title("box", "Genre Summary Table")
            with st.expander("View Genre Summary — Detail Table", expanded=True):
                ct         = df_cat.copy()
                ct.columns = ["Genre", "Rentals", "Total Revenue ($)", "Films", "Revenue / Film ($)"]
                ct["Total Revenue ($)"]  = ct["Total Revenue ($)"].map("${:,.2f}".format)
                ct["Revenue / Film ($)"] = ct["Revenue / Film ($)"].map("${:,.2f}".format)
                st.dataframe(ct.reset_index(drop=True), use_container_width=True)

        tg  = df_cat.nlargest(1, "total_revenue").iloc[0]
        tpf = df_cat.nlargest(1, "revenue_per_film").iloc[0]
        _panel("panel-positive", "#15803d", "Genre Insight", [
            f"Highest gross genre: <strong>{tg['category']}</strong> — ${tg['total_revenue']:,.2f} total revenue.",
            f"Best revenue per film: <strong>{tpf['category']}</strong> — ${tpf['revenue_per_film']:,.2f} per title. Every new purchase in this genre is likely to be profitable.",
        ])