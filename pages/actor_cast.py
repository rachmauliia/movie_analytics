"""
Feature 4 — Actor & Cast Star Power Analysis
"Which actors drive rentals and revenue?"
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.cards import kpi_card, page_header, section_title
from db import run_query

# ── Design tokens ─────────────────────────────────────────────────────────────
PURPLE = "#6c5ce7"
TEAL   = "#00b894"
ORANGE = "#fd9644"
PINK   = "#fd79a8"
BLUE   = "#0984e3"
RED    = "#d63031"

RATING_COLORS = {
    "G":     "#1e8449",
    "PG":    "#1a5276",
    "PG-13": "#d68910",
    "R":     "#c0392b",
    "NC-17": "#6c3483",
}

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
.panel-warning  { background: #fffbeb; border: 1px solid #fde68a; border-left: 4px solid #d97706; }
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
SQL_ACTOR_REVENUE = """
SELECT
    a.actor_id,
    a.first_name || ' ' || a.last_name           AS actor,
    COUNT(DISTINCT f.film_id)                    AS film_count,
    COUNT(r.rental_id)                           AS rental_count,
    ROUND(COALESCE(SUM(p.amount),0),2)           AS total_revenue,
    ROUND(COALESCE(SUM(p.amount),0)
        / NULLIF(COUNT(DISTINCT f.film_id),0),2) AS revenue_per_film
FROM actor a
JOIN film_actor fa    ON a.actor_id     = fa.actor_id
JOIN film f           ON fa.film_id     = f.film_id
LEFT JOIN inventory i ON f.film_id     = i.film_id
LEFT JOIN rental r    ON i.inventory_id = r.inventory_id
LEFT JOIN payment p   ON r.rental_id   = p.rental_id
GROUP BY a.actor_id, a.first_name, a.last_name
ORDER BY total_revenue DESC;
"""

SQL_ACTOR_GENRE = """
SELECT
    a.first_name || ' ' || a.last_name  AS actor,
    c.name                              AS genre,
    COUNT(r.rental_id)                  AS rentals
FROM actor a
JOIN film_actor fa    ON a.actor_id     = fa.actor_id
JOIN film f           ON fa.film_id     = f.film_id
JOIN film_category fc ON f.film_id     = fc.film_id
JOIN category c       ON fc.category_id = c.category_id
LEFT JOIN inventory i ON f.film_id     = i.film_id
LEFT JOIN rental r    ON i.inventory_id = r.inventory_id
GROUP BY 1, 2
ORDER BY rentals DESC;
"""

SQL_CAST_SIZE = """
SELECT
    f.film_id,
    f.title,
    f.rating::text                          AS rating,
    c.name                                  AS genre,
    COUNT(DISTINCT fa.actor_id)             AS cast_size,
    COUNT(r.rental_id)                      AS rental_count,
    ROUND(COALESCE(SUM(p.amount),0),2)      AS total_revenue
FROM film f
JOIN film_actor fa    ON fa.film_id     = f.film_id
JOIN film_category fc ON fc.film_id    = f.film_id
JOIN category c       ON c.category_id = fc.category_id
LEFT JOIN inventory i ON i.film_id     = f.film_id
LEFT JOIN rental r    ON r.inventory_id = i.inventory_id
LEFT JOIN payment p   ON p.rental_id   = r.rental_id
GROUP BY f.film_id, f.title, f.rating, c.name
ORDER BY total_revenue DESC;
"""

SQL_GENRES = "SELECT DISTINCT name AS genre FROM category ORDER BY name;"

SQL_ACTOR_LIST = """
SELECT actor_id,
       first_name || ' ' || last_name AS actor
FROM actor
ORDER BY last_name, first_name;
"""


@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    return (
        run_query(SQL_ACTOR_REVENUE),
        run_query(SQL_ACTOR_GENRE),
        run_query(SQL_CAST_SIZE),
        run_query(SQL_GENRES),
        run_query(SQL_ACTOR_LIST),
    )


# ── Film popularity score (0–100) ─────────────────────────────────────────────
def _film_score(actor_rpf_map, actors, genre, rating, genre_w, rating_w):
    avg_rpf    = float(np.mean([actor_rpf_map.get(a, 0) for a in actors])) if actors else 0.0
    max_rpf    = max(actor_rpf_map.values()) if actor_rpf_map else 1
    max_genre  = max(genre_w.values())       if genre_w      else 1
    max_rating = max(rating_w.values())      if rating_w     else 1

    score = (
        (avg_rpf / max_rpf)                      * 0.40
        + (genre_w.get(genre, 0)   / max_genre)  * 0.35
        + (rating_w.get(rating, 0) / max_rating) * 0.25
    ) * 100
    return round(score, 1)


# ── MAIN ──────────────────────────────────────────────────────────────────────
def render():
    st.markdown(CARD_CSS, unsafe_allow_html=True)

    page_header(
        "Actor & Cast Star Power Analysis",
        "Which actors and casts drive the most rentals and revenue?",
        "Feature 4",
    )

    with st.spinner("Loading data..."):
        df_ar, df_ag, df_cast, df_genres, df_actor_list = load_data()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        '<p style="font-size:0.7rem;font-weight:600;text-transform:uppercase;'
        'letter-spacing:0.08em;color:#9da3bd;margin-bottom:0.4rem;">Filters</p>',
        unsafe_allow_html=True,
    )
    top_n = st.sidebar.slider("Top N Actors", 5, 30, 15, key="ac_n")

    # ── KPI ───────────────────────────────────────────────────────────────────
    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
    top_actor   = df_ar.nlargest(1, "total_revenue").iloc[0]
    top_rentals = df_ar.nlargest(1, "rental_count").iloc[0]
    best_rpf    = df_ar.nlargest(1, "revenue_per_film").iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Total Actors",      str(df_ar["actor"].nunique()),           "In the catalog",              "purple", "users")
    with c2:
        kpi_card("Top Revenue Actor", top_actor["actor"],                      f"${top_actor['total_revenue']:,.2f}", "teal", "dollar")
    with c3:
        kpi_card("Most Rented Actor", top_rentals["actor"],                    f"{int(top_rentals['rental_count']):,} rentals", "orange", "star")
    with c4:
        kpi_card("Best Rev / Film",   best_rpf["actor"],                       f"${best_rpf['revenue_per_film']:,.2f}", "pink", "trend")

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "Revenue & Rentals",
        "Cast Size Impact",
        "Efficiency Quadrant",
    ])

    # ═══════════ TAB 1 ─ Revenue & Rentals ════════════════════════════════════
    with tab1:
        top_df = df_ar.head(top_n)

        c1, c2 = st.columns(2)
        with c1:
            section_title("dollar", f"Top {top_n} Actors by Revenue")
            chart_desc("Horizontal bar chart ranking actors by total revenue generated across all their films. Color intensity reflects the revenue magnitude.")
            fig = px.bar(
                top_df.sort_values("total_revenue"),
                x="total_revenue", y="actor", orientation="h",
                color="total_revenue",
                color_continuous_scale=["#a29bfe", PURPLE],
                labels={"total_revenue": "Revenue ($)", "actor": "Actor"},
                hover_data=["film_count", "rental_count"],
            )
            fig.update_layout(
                **PL, height=max(320, top_n * 28),
                coloraxis_showscale=False,
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with c2:
            section_title("film", f"Top {top_n} Actors by Rental Count")
            chart_desc("Ranks actors by total number of rentals across all their films — a direct measure of how frequently customers choose their movies.")
            top_rent_df = df_ar.nlargest(top_n, "rental_count")
            fig2 = px.bar(
                top_rent_df.sort_values("rental_count"),
                x="rental_count", y="actor", orientation="h",
                color="rental_count",
                color_continuous_scale=["#55efc4", TEAL],
                labels={"rental_count": "Rentals", "actor": "Actor"},
                hover_data=["film_count", "total_revenue"],
            )
            fig2.update_layout(
                **PL, height=max(320, top_n * 28),
                coloraxis_showscale=False,
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        # Inline insight
        top5_rev = df_ar.head(5)["actor"].tolist()
        _panel("panel-positive", "#15803d", "Revenue & Rental Insight", [
            f"Top revenue actor: <strong>{top_actor['actor']}</strong> — ${top_actor['total_revenue']:,.2f} across {int(top_actor['film_count'])} films.",
            f"Most rented actor: <strong>{top_rentals['actor']}</strong> — {int(top_rentals['rental_count']):,} total rentals.",
            f"Top 5 by revenue: <strong>{', '.join(top5_rev)}</strong> — maintain consistent stock availability for their titles.",
        ])

        section_title("trend", "Revenue vs Films Bubble Chart (Top 30)")
        chart_desc("Scatter plot comparing each actor's number of films (x-axis) against total revenue (y-axis). Bubble size reflects rental count; color reflects revenue per film. Actors in the upper-right area are both prolific and high-earning.")
        top30 = df_ar.head(30)
        fig_bub = px.scatter(
            top30, x="film_count", y="total_revenue",
            size="rental_count", text="actor",
            color="revenue_per_film",
            color_continuous_scale=["#a29bfe", PURPLE],
            labels={
                "film_count":       "Number of Films",
                "total_revenue":    "Total Revenue ($)",
                "rental_count":     "Rentals",
                "revenue_per_film": "Rev/Film ($)",
            },
            size_max=40,
        )
        fig_bub.update_traces(textposition="top center", textfont_size=9)
        fig_bub.update_layout(**PL, height=420)
        st.plotly_chart(fig_bub, use_container_width=True, config={"displayModeBar": False})

        section_title("box", "Full Actor Table (Top 50)")
        chart_desc("Complete ranking of the top 50 actors by revenue, including film count, total rentals, and efficiency metrics.")
        disp         = df_ar.head(50).copy()
        disp.index   = range(1, len(disp) + 1)
        disp.columns = ["ID", "Actor", "Films", "Rentals", "Revenue ($)", "Revenue/Film ($)"]
        disp["Revenue ($)"]      = disp["Revenue ($)"].map("${:,.2f}".format)
        disp["Revenue/Film ($)"] = disp["Revenue/Film ($)"].map("${:,.2f}".format)
        st.dataframe(disp.drop(columns=["ID"]), use_container_width=True)

    # ═══════════ TAB 2 ─ Cast Size Impact ═════════════════════════════════════
    with tab2:
        section_title("users", "Does a Larger Cast Mean Higher Revenue?")
        chart_desc("Each dot represents one film. The x-axis shows the number of actors in the cast; the y-axis shows total revenue. The OLS trendline reveals whether cast size has a statistically meaningful relationship with revenue. Bubble size reflects rental count.")
        st.markdown(
            "<p style='font-size:0.83rem;color:#374151;margin-bottom:0.6rem;'>"
            "This chart answers: <strong>does the number of actors in a film affect how much it earns?</strong> "
            "Films are colored by rating. The trendline shows the overall direction of the relationship."
            "</p>",
            unsafe_allow_html=True,
        )

        fig_sc = px.scatter(
            df_cast,
            x="cast_size", y="total_revenue",
            color="rating", size="rental_count", size_max=22,
            color_discrete_map=RATING_COLORS,
            trendline="ols",
            hover_data=["title", "genre"],
            labels={
                "cast_size":     "Number of Actors in Film",
                "total_revenue": "Total Revenue ($)",
                "rental_count":  "Rentals",
            },
        )
        fig_sc.update_layout(**PL, height=400)
        st.plotly_chart(fig_sc, use_container_width=True, config={"displayModeBar": False})

        # Correlation metrics
        corr_rev  = df_cast[["cast_size", "total_revenue"]].corr().iloc[0, 1]
        corr_rent = df_cast[["cast_size", "rental_count"]].corr().iloc[0, 1]
        m1, m2    = st.columns(2)
        m1.metric("Correlation: Cast Size vs Revenue", f"{corr_rev:.3f}", help="Range: -1 (negative) to +1 (positive). Values near 0 indicate no meaningful relationship.")
        m2.metric("Correlation: Cast Size vs Rentals", f"{corr_rent:.3f}", help="Range: -1 to +1.")

        if corr_rev > 0.2:
            _panel("panel-positive", "#15803d", "Cast Size Finding", [
                f"Positive correlation detected between cast size and revenue ({corr_rev:.3f}).",
                "Films with larger casts tend to generate higher revenue.",
                "Consider prioritizing films with 10+ actors when selecting new inventory.",
            ])
        else:
            _panel("panel-warning", "#d97706", "Cast Size Finding", [
                f"Correlation between cast size and revenue is very weak ({corr_rev:.3f}).",
                "Number of actors alone is not a reliable predictor of revenue.",
                "<strong>Genre and rating are far more influential</strong> than cast size when selecting new stock.",
            ])

    # ═══════════ TAB 3 ─ Efficiency Quadrant ══════════════════════════════════
    with tab3:
        section_title("grid", "Actor Efficiency Quadrant")
        chart_desc("Divides actors into 4 strategic groups based on two dimensions: number of films (productivity) and revenue per film (efficiency). The dashed lines represent median values. Bubble size reflects total revenue.")
        st.markdown(
            "<p style='font-size:0.83rem;color:#374151;margin-bottom:0.6rem;'>"
            "This quadrant helps prioritize which actors to invest in for future stock purchasing decisions."
            "</p>",
            unsafe_allow_html=True,
        )

        top_q   = df_ar.head(40).copy()
        med_fc  = top_q["film_count"].median()
        med_rpf = top_q["revenue_per_film"].median()

        def _quad(row):
            hi_f = row["film_count"]       >= med_fc
            hi_r = row["revenue_per_film"] >= med_rpf
            if     hi_f and     hi_r: return "Stars"
            if not hi_f and     hi_r: return "Hidden Gems"
            if     hi_f and not hi_r: return "Quantity Players"
            return                            "Underperformers"

        top_q["quadrant"] = top_q.apply(_quad, axis=1)

        Q_COLORS = {
            "Stars":            TEAL,
            "Hidden Gems":      PURPLE,
            "Quantity Players": ORANGE,
            "Underperformers":  "#b2bec3",
        }

        fig_q = px.scatter(
            top_q,
            x="film_count", y="revenue_per_film",
            size="total_revenue", color="quadrant", text="actor",
            color_discrete_map=Q_COLORS, size_max=38,
            labels={
                "film_count":       "Number of Films",
                "revenue_per_film": "Revenue per Film ($)",
                "total_revenue":    "Total Revenue ($)",
                "quadrant":         "Quadrant",
            },
        )
        fig_q.update_traces(textposition="top center", textfont_size=8.5)
        fig_q.add_vline(x=med_fc,  line_dash="dash", line_color="#ccc", line_width=1.2)
        fig_q.add_hline(y=med_rpf, line_dash="dash", line_color="#ccc", line_width=1.2)

        x_max = top_q["film_count"].max()
        x_min = top_q["film_count"].min()
        y_max = top_q["revenue_per_film"].max()
        y_min = top_q["revenue_per_film"].min()
        for lbl, ax, ay, ac in [
            ("Stars",            x_max, y_max, TEAL),
            ("Hidden Gems",      x_min, y_max, PURPLE),
            ("Quantity Players", x_max, y_min, ORANGE),
            ("Underperformers",  x_min, y_min, "#888"),
        ]:
            fig_q.add_annotation(
                x=ax, y=ay, text=lbl, showarrow=False,
                font=dict(color=ac, size=10, family="Inter"),
            )

        fig_q.update_layout(**PL, height=520)
        st.plotly_chart(fig_q, use_container_width=True, config={"displayModeBar": False})

        # Quadrant summary cards
        q_counts = top_q["quadrant"].value_counts()
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        qa, qb, qc, qd = st.columns(4)

        for col_w, key, color, strategy in [
            (qa, "Stars",            TEAL,    "Top priority — always stock more of their films"),
            (qb, "Hidden Gems",      PURPLE,  "Highly efficient — seek more titles from them"),
            (qc, "Quantity Players", ORANGE,  "Many films, lower efficiency — be more selective"),
            (qd, "Underperformers",  "#b2bec3", "Review and consider reducing new stock"),
        ]:
            n = q_counts.get(key, 0)
            col_w.markdown(
                f"""
                <div style="background:#fff;border-radius:14px;
                     border:1px solid #edeef8;border-top:3px solid {color};
                     box-shadow:0 2px 10px rgba(0,0,0,0.04);
                     padding:1rem 1.1rem;text-align:center;">
                  <div style="font-weight:700;font-size:0.82rem;
                       color:#1a1c2e;margin-bottom:0.15rem;">{key}</div>
                  <div style="font-size:1.6rem;font-weight:700;color:{color};">{n}</div>
                  <div style="font-size:0.66rem;color:#9da3bd;margin-top:0.25rem;
                       line-height:1.4;">{strategy}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

        # Inline insight
        stars_actors = top_q[top_q["quadrant"] == "Stars"]["actor"].head(3).tolist()
        gems_actors  = top_q[top_q["quadrant"] == "Hidden Gems"]["actor"].head(3).tolist()
        _panel("panel-positive", "#15803d", "Quadrant Insight", [
            f"Star actors: <strong>{', '.join(stars_actors)}</strong> — both prolific and efficient. Prioritize their films in all purchasing decisions.",
            f"Hidden Gems: <strong>{', '.join(gems_actors)}</strong> — fewer films but exceptional revenue per title. Actively seek new films featuring these actors.",
        ])
        _panel("panel-negative", "#b91c1c", "Quadrant Concern", [
            f"<strong>{q_counts.get('Underperformers', 0)} actors</strong> fall in the Underperformers quadrant — review new stock decisions for their titles.",
            f"<strong>{q_counts.get('Quantity Players', 0)} Quantity Players</strong> have many films but below-median efficiency — apply stricter selection criteria.",
        ])

        with st.expander("Detailed Quadrant Table"):
            disp_q             = top_q[["actor", "quadrant", "film_count", "rental_count", "total_revenue", "revenue_per_film"]].copy()
            disp_q["total_revenue"]    = disp_q["total_revenue"].map("${:,.2f}".format)
            disp_q["revenue_per_film"] = disp_q["revenue_per_film"].map("${:,.2f}".format)
            disp_q.columns     = ["Actor", "Quadrant", "Films", "Rentals", "Revenue", "Rev/Film"]
            st.dataframe(disp_q, use_container_width=True, hide_index=True)
