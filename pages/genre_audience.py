"""
Feature 2 — Genre & Audience Taste Analysis
"What does our audience actually want to watch?"
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.cards import kpi_card, page_header, section_title
from db import run_query

PURPLE = "#6c5ce7"
TEAL   = "#00b894"
ORANGE = "#fd9644"
PINK   = "#fd79a8"
BLUE   = "#0984e3"

RATING_COLORS = {
    "G": "#1e8449", "PG": "#1a5276",
    "PG-13": "#d68910", "R": "#c0392b", "NC-17": "#6c3483",
}

PL = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", size=11, color="#1a1c2e"),
    margin=dict(l=10, r=10, t=24, b=10),
    legend=dict(bgcolor="rgba(255,255,255,0.85)", bordercolor="#edeef8",
                borderwidth=1, font=dict(size=10)),
)

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
.insight-panel ul { margin: 0.35rem 0 0 0; padding-left: 1.2rem; }
.insight-panel li  { margin-bottom: 0.3rem; }
.panel-positive { background: #f0fdf4; border: 1px solid #bbf7d0; border-left: 4px solid #16a34a; }
.panel-negative { background: #fff5f5; border: 1px solid #fecaca; border-left: 4px solid #dc2626; }
.panel-action   { background: #eff6ff; border: 1px solid #bfdbfe; border-left: 4px solid #2563eb; }
.panel-title    { font-weight: 700; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }
.chart-desc     { font-size: 0.78rem; color: #6b7280; margin: -0.2rem 0 0.6rem 0; font-style: italic; }
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


# ── SQL ────────────────────────────────────────────────────────────────────────
SQL_GENRE_RATING = """
SELECT
    c.name                          AS genre,
    f.rating::text                  AS rating,
    COUNT(r.rental_id)              AS rentals,
    COUNT(DISTINCT f.film_id)       AS film_count
FROM category c
JOIN film_category fc ON c.category_id = fc.category_id
JOIN film f           ON fc.film_id    = f.film_id
LEFT JOIN inventory i ON f.film_id     = i.film_id
LEFT JOIN rental r    ON i.inventory_id = r.inventory_id
GROUP BY c.name, f.rating
ORDER BY rentals DESC;
"""

SQL_GENRE_TREND = """
SELECT
    DATE_TRUNC('month', r.rental_date)::date AS month,
    c.name                                   AS genre,
    COUNT(r.rental_id)                       AS rentals
FROM rental r
JOIN inventory i    ON r.inventory_id = i.inventory_id
JOIN film f         ON i.film_id      = f.film_id
JOIN film_category fc ON f.film_id   = fc.film_id
JOIN category c     ON fc.category_id = c.category_id
GROUP BY 1, 2
ORDER BY 1, 2;
"""

SQL_LANG = """
SELECT
    l.name                          AS language,
    COUNT(DISTINCT f.film_id)       AS film_count,
    COUNT(r.rental_id)              AS rentals
FROM language l
JOIN film f         ON l.language_id  = f.language_id
LEFT JOIN inventory i ON f.film_id   = i.film_id
LEFT JOIN rental r  ON i.inventory_id = r.inventory_id
GROUP BY l.name
ORDER BY rentals DESC;
"""

SQL_LENGTH_BUCKET = """
SELECT
    CASE
        WHEN f.length < 60  THEN 'Under 60 min'
        WHEN f.length < 90  THEN '60-89 min'
        WHEN f.length < 120 THEN '90-119 min'
        WHEN f.length < 150 THEN '120-149 min'
        ELSE '150+ min'
    END                             AS length_bucket,
    COUNT(r.rental_id)              AS rentals,
    ROUND(AVG(p.amount),2)          AS avg_payment
FROM film f
LEFT JOIN inventory i   ON f.film_id      = i.film_id
LEFT JOIN rental r      ON i.inventory_id = r.inventory_id
LEFT JOIN payment p     ON r.rental_id    = p.rental_id
GROUP BY 1
ORDER BY MIN(f.length);
"""

SQL_GENRE_SUMMARY = """
SELECT
    c.name                                      AS genre,
    COUNT(DISTINCT f.film_id)                   AS film_count,
    COUNT(r.rental_id)                          AS rentals,
    ROUND(COALESCE(SUM(p.amount),0),2)          AS revenue,
    ROUND(COALESCE(SUM(p.amount),0)
        / NULLIF(COUNT(DISTINCT f.film_id),0),2) AS revenue_per_film,
    ROUND(COALESCE(SUM(p.amount),0)
        / NULLIF(COUNT(r.rental_id),0),2)        AS revenue_per_rental
FROM category c
JOIN film_category fc   ON c.category_id = fc.category_id
JOIN film f             ON fc.film_id    = f.film_id
LEFT JOIN inventory i   ON f.film_id     = i.film_id
LEFT JOIN rental r      ON i.inventory_id = r.inventory_id
LEFT JOIN payment p     ON r.rental_id   = p.rental_id
GROUP BY c.name
ORDER BY rentals DESC;
"""


@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    return (
        run_query(SQL_GENRE_RATING),
        run_query(SQL_GENRE_TREND),
        run_query(SQL_LANG),
        run_query(SQL_LENGTH_BUCKET),
        run_query(SQL_GENRE_SUMMARY),
    )


def render():
    st.markdown(CARD_CSS, unsafe_allow_html=True)

    page_header(
        "Genre & Audience Taste Analysis",
        "What does our audience actually want to watch?",
        "Feature 2",
    )

    with st.spinner("Loading data..."):
        df_gr, df_gt, df_lang, df_len, df_gs = load_data()

    # Sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        '<p style="font-size:0.7rem;font-weight:600;text-transform:uppercase;'
        'letter-spacing:0.08em;color:#9da3bd;margin-bottom:0.4rem;">Filters</p>',
        unsafe_allow_html=True,
    )
    top_genres_n = st.sidebar.slider("Top N Genres", 5, 16, 10, key="ga_n")
    all_genres   = sorted(df_gs["genre"].unique().tolist())
    sel_genres   = st.sidebar.multiselect("Genres", all_genres, default=all_genres[:8], key="ga_g")

    # ── KPI ───────────────────────────────────────────────────────────────────
    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
    total_genres  = df_gs["genre"].nunique()
    top_genre_row = df_gs.nlargest(1, "rentals").iloc[0]
    best_rpf      = df_gs.nlargest(1, "revenue_per_film").iloc[0]
    total_rent    = df_gs["rentals"].sum()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Total Genres",      str(total_genres),                      "Unique categories",          "purple", "tag")
    with c2:
        kpi_card("Most Rented Genre", top_genre_row["genre"],                 f"{int(top_genre_row['rentals']):,} rentals", "teal", "star")
    with c3:
        kpi_card("Best ROI Genre",    best_rpf["genre"],                      f"${best_rpf['revenue_per_film']:,.2f} / film", "orange", "trend")
    with c4:
        kpi_card("Total Rentals",     f"{int(total_rent):,}",                 "Across all categories",      "blue",   "film")

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "Genre Performance",
        "Trends Over Time",
        "Film Attributes",
    ])

    # ── Tab 1 ─────────────────────────────────────────────────────────────────
    with tab1:
        section_title("bar", f"Top {top_genres_n} Genres by Rentals vs Revenue")
        top_gs = df_gs.nlargest(top_genres_n, "rentals")

        c1, c2 = st.columns(2)
        with c1:
            chart_desc("Ranks genres by total rental volume — reflects raw audience demand for each category.")
            fig = px.bar(
                top_gs.sort_values("rentals"),
                x="rentals", y="genre", orientation="h",
                color="rentals", color_continuous_scale=["#a29bfe", PURPLE],
                labels={"rentals": "Rentals", "genre": "Genre"},
                hover_data=["film_count", "revenue"],
            )
            fig.update_layout(**PL, height=400, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with c2:
            chart_desc("Ranks genres by total revenue generated — reflects both audience demand and the monetary value each genre delivers.")
            fig2 = px.bar(
                top_gs.sort_values("revenue"),
                x="revenue", y="genre", orientation="h",
                color="revenue", color_continuous_scale=["#55efc4", TEAL],
                labels={"revenue": "Revenue ($)", "genre": "Genre"},
                hover_data=["film_count", "revenue_per_film"],
            )
            fig2.update_layout(**PL, height=400, coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        # Inline insight after charts
        top3_genres    = df_gs.nlargest(3, "rentals")["genre"].tolist()
        bottom3_genres = df_gs.nsmallest(3, "rentals")["genre"].tolist()
        _panel("panel-positive", "#15803d", "Genre Performance Insight", [
            f"Top 3 genres by rental volume: <strong>{', '.join(top3_genres)}</strong> — consistently strong audience demand.",
            f"Most efficient genre (revenue/film): <strong>{best_rpf['genre']}</strong> at ${best_rpf['revenue_per_film']:,.2f}/film. Every new title added generates a strong return.",
            f"Best-grossing genre overall: <strong>{df_gs.nlargest(1, 'revenue').iloc[0]['genre']}</strong> — proven to drive the highest total income.",
        ])
        _panel("panel-negative", "#b91c1c", "Underperforming Genres", [
            f"Lowest rental genres: <strong>{', '.join(bottom3_genres)}</strong> — evaluate whether current stock levels match actual demand.",
            f"{len(df_gs[df_gs['revenue_per_film'] < df_gs['revenue_per_film'].mean()])} genres are below average revenue per film — stock investment in these categories is less efficient.",
        ])

        section_title("star", "Genre x Rating Heatmap — Rental Volume")
        chart_desc("Each cell shows how many rentals a genre-rating combination received. Darker cells indicate higher demand. Use this to identify which genre and rating pairings resonate most with your audience.")
        pivot  = df_gr.pivot_table(index="genre", columns="rating", values="rentals", fill_value=0)
        fig_h  = px.imshow(
            pivot, color_continuous_scale=["#f4f5fb", PURPLE],
            labels=dict(x="Rating", y="Genre", color="Rentals"),
            aspect="auto",
        )
        fig_h.update_layout(**PL, height=460)
        st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})

        _panel("panel-action", "#1d4ed8", "Heatmap Insight", [
            "High-intensity cells represent genre + rating combinations with proven audience demand — prioritize these when selecting new inventory.",
            "Sparse rows indicate genres that perform poorly regardless of rating — reducing stock depth in these rows is advisable.",
        ])

        section_title("box", "Full Genre Summary Table")
        disp         = df_gs.copy()
        disp.columns = ["Genre", "Films", "Rentals", "Revenue ($)", "Revenue/Film ($)", "Revenue/Rental ($)"]
        disp["Revenue ($)"]        = disp["Revenue ($)"].map("${:,.2f}".format)
        disp["Revenue/Film ($)"]   = disp["Revenue/Film ($)"].map("${:,.2f}".format)
        disp["Revenue/Rental ($)"] = disp["Revenue/Rental ($)"].map("${:,.2f}".format)
        st.dataframe(disp.reset_index(drop=True), use_container_width=True)

    # ── Tab 2 ─────────────────────────────────────────────────────────────────
    with tab2:
        section_title("trend", "Monthly Rental Trend by Genre")
        filt_gt = df_gt[df_gt["genre"].isin(sel_genres)] if sel_genres else df_gt

        colors_cycle   = [PURPLE, TEAL, ORANGE, PINK, BLUE, "#a29bfe", "#55efc4", "#fecb52", "#74b9ff", "#fab1d3"]
        genre_color_map = {g: colors_cycle[i % len(colors_cycle)] for i, g in enumerate(sel_genres)}

        chart_desc("Line chart tracking monthly rental volume per genre over time. Rising lines indicate growing audience interest; declining lines may signal a need to refresh that genre's catalog.")
        fig_trend = px.line(
            filt_gt, x="month", y="rentals", color="genre",
            color_discrete_map=genre_color_map,
            labels={"month": "Month", "rentals": "Rentals", "genre": "Genre"},
        )
        fig_trend.update_traces(line=dict(width=2))
        fig_trend.update_layout(**PL, height=360, yaxis=dict(gridcolor="#f0f1f8"))
        st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

        _panel("panel-action", "#1d4ed8", "Trend Insight", [
            "Genres showing consistent upward trends are good candidates for additional stock investment.",
            "Genres with declining or flat trends may indicate audience saturation — consider refreshing with new titles rather than adding copies of existing ones.",
        ])

    # ── Tab 3 ─────────────────────────────────────────────────────────────────
    with tab3:
        section_title("film", "Rentals by Film Length")
        chart_desc("Compares rental volume across different film duration buckets. Shows which runtime range is most popular with your customer base — useful for guiding future purchasing decisions.")
        fig_len = px.bar(
            df_len, x="length_bucket", y="rentals",
            color="rentals", color_continuous_scale=["#a29bfe", PURPLE],
            labels={"length_bucket": "Film Length", "rentals": "Rentals"},
            text="rentals",
        )
        fig_len.update_traces(textposition="outside")
        fig_len.update_layout(**PL, height=320, coloraxis_showscale=False)
        st.plotly_chart(fig_len, use_container_width=True, config={"displayModeBar": False})

        top_len = df_len.loc[df_len["rentals"].idxmax(), "length_bucket"]
        low_len = df_len.loc[df_len["rentals"].idxmin(), "length_bucket"]
        _panel("panel-positive", "#15803d", "Film Length Insight", [
            f"Most popular runtime: <strong>{top_len}</strong> — align future purchasing toward this duration range.",
            f"Least popular runtime: <strong>{low_len}</strong> — avoid over-stocking films in this range.",
        ])

        section_title("dollar", "Language Distribution in Catalog")
        chart_desc("Shows how many rentals each language in the catalog has received. Useful for understanding whether language diversity in inventory is aligned with customer demand.")
        fig_lang = px.bar(
            df_lang, x="language", y="rentals",
            color="rentals", color_continuous_scale=["#55efc4", TEAL],
            labels={"language": "Language", "rentals": "Rentals"},
            text="rentals",
        )
        fig_lang.update_traces(textposition="outside")
        fig_lang.update_layout(**PL, height=280, coloraxis_showscale=False)
        st.plotly_chart(fig_lang, use_container_width=True, config={"displayModeBar": False})
