"""
Feature 3 — Rental Behavior & Late Return Analysis
"When do customers rent, how long do they keep films, and who returns late?"
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
RED    = "#d63031"

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
SQL_RENTAL_DURATION = """
SELECT
    EXTRACT(DOW FROM r.rental_date)::int        AS dow,
    TO_CHAR(r.rental_date,'Day')                AS day_name,
    COUNT(r.rental_id)                          AS rentals,
    ROUND(AVG(EXTRACT(EPOCH FROM
        (r.return_date - r.rental_date))/86400),2) AS avg_days
FROM rental r
WHERE r.return_date IS NOT NULL
GROUP BY 1,2
ORDER BY 1;
"""

SQL_HOURLY = """
SELECT
    EXTRACT(HOUR FROM r.rental_date)::int       AS hour,
    COUNT(r.rental_id)                          AS rentals
FROM rental r
GROUP BY 1
ORDER BY 1;
"""

SQL_LATE = """
SELECT
    r.rental_id,
    f.title,
    f.rating::text                              AS rating,
    f.rental_duration,
    EXTRACT(EPOCH FROM
        (r.return_date - r.rental_date))/86400  AS actual_days,
    EXTRACT(EPOCH FROM
        (r.return_date - r.rental_date))/86400
        - f.rental_duration                     AS days_late,
    c.first_name || ' ' || c.last_name          AS customer_name
FROM rental r
JOIN inventory i    ON r.inventory_id   = i.inventory_id
JOIN film f         ON i.film_id        = f.film_id
JOIN customer c     ON r.customer_id    = c.customer_id
WHERE r.return_date IS NOT NULL
  AND EXTRACT(EPOCH FROM
        (r.return_date - r.rental_date))/86400 > f.rental_duration
ORDER BY days_late DESC
LIMIT 200;
"""

SQL_LATE_CUSTOMER = """
SELECT
    c.first_name || ' ' || c.last_name          AS customer,
    COUNT(r.rental_id)                          AS late_returns,
    ROUND(AVG(
        EXTRACT(EPOCH FROM
            (r.return_date - r.rental_date))/86400
        - f.rental_duration
    ),2)                                        AS avg_days_late
FROM rental r
JOIN inventory i    ON r.inventory_id   = i.inventory_id
JOIN film f         ON i.film_id        = f.film_id
JOIN customer c     ON r.customer_id    = c.customer_id
WHERE r.return_date IS NOT NULL
  AND EXTRACT(EPOCH FROM
        (r.return_date - r.rental_date))/86400 > f.rental_duration
GROUP BY 1
ORDER BY late_returns DESC
LIMIT 20;
"""

SQL_MONTHLY_RENTALS = """
SELECT
    DATE_TRUNC('month', rental_date)::date      AS month,
    COUNT(rental_id)                            AS rentals
FROM rental
GROUP BY 1
ORDER BY 1;
"""

SQL_RETURN_STATUS = """
SELECT
    CASE
        WHEN return_date IS NULL THEN 'Not Returned'
        WHEN EXTRACT(EPOCH FROM (return_date - rental_date))/86400 > f.rental_duration
            THEN 'Late'
        ELSE 'On Time'
    END                                         AS status,
    COUNT(*)                                    AS count
FROM rental r
JOIN inventory i ON r.inventory_id = i.inventory_id
JOIN film f      ON i.film_id      = f.film_id
GROUP BY 1;
"""


@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    return (
        run_query(SQL_RENTAL_DURATION),
        run_query(SQL_HOURLY),
        run_query(SQL_LATE),
        run_query(SQL_LATE_CUSTOMER),
        run_query(SQL_MONTHLY_RENTALS),
        run_query(SQL_RETURN_STATUS),
    )


def render():
    st.markdown(CARD_CSS, unsafe_allow_html=True)

    page_header(
        "Rental Behavior & Late Return Analysis",
        "When do customers rent, how long do they keep films, and who returns late?",
        "Feature 3",
    )

    with st.spinner("Loading data..."):
        df_dur, df_hr, df_late, df_late_cust, df_mo, df_status = load_data()

    # ── KPI ───────────────────────────────────────────────────────────────────
    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    total_rentals = df_mo["rentals"].sum()
    late_count    = int(df_status[df_status["status"] == "Late"]["count"].sum())
    not_ret       = int(df_status[df_status["status"] == "Not Returned"]["count"].sum()) if "Not Returned" in df_status["status"].values else 0
    on_time       = int(df_status[df_status["status"] == "On Time"]["count"].sum())
    late_pct      = late_count / max(total_rentals, 1) * 100
    avg_dur       = df_dur["avg_days"].mean()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("Total Rentals",   f"{int(total_rentals):,}", "All time",                "purple", "film")
    with c2:
        kpi_card("On Time Returns", f"{on_time:,}",            "Returned within period",  "teal",   "check")
    with c3:
        kpi_card("Late Returns",    f"{late_count:,}",         f"{late_pct:.1f}% of rentals", "red", "warn")
    with c4:
        kpi_card("Not Returned",    f"{not_ret:,}",            "Still outstanding",       "orange", "clock")
    with c5:
        kpi_card("Avg Rental Days", f"{avg_dur:.1f}",          "Average across weekdays", "blue",   "bar")

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "Rental Patterns",
        "Late Returns",
        "Monthly Trends",
    ])

    # ── Tab 1 ─────────────────────────────────────────────────────────────────
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            section_title("bar", "Rentals by Day of Week")
            chart_desc("Shows which days of the week generate the most rental activity. Useful for scheduling promotions and optimizing staffing levels.")
            fig_dow = px.bar(
                df_dur, x="day_name", y="rentals",
                color="rentals", color_continuous_scale=["#a29bfe", PURPLE],
                labels={"day_name": "Day", "rentals": "Rentals"},
                text="rentals",
            )
            fig_dow.update_traces(textposition="outside")
            fig_dow.update_layout(**PL, height=320, coloraxis_showscale=False)
            st.plotly_chart(fig_dow, use_container_width=True, config={"displayModeBar": False})

        with c2:
            section_title("clock", "Rentals by Hour of Day")
            chart_desc("Displays rental volume for each hour of the day. Peak hours indicate when customers are most active — useful for staffing and system capacity planning.")
            fig_hr = px.bar(
                df_hr, x="hour", y="rentals",
                color="rentals", color_continuous_scale=["#55efc4", TEAL],
                labels={"hour": "Hour", "rentals": "Rentals"},
            )
            fig_hr.update_layout(**PL, height=320, coloraxis_showscale=False)
            st.plotly_chart(fig_hr, use_container_width=True, config={"displayModeBar": False})

        # Inline insight after the two charts
        peak_day  = df_dur.loc[df_dur["rentals"].idxmax(), "day_name"].strip()
        slow_day  = df_dur.loc[df_dur["rentals"].idxmin(), "day_name"].strip()
        peak_hour = int(df_hr.loc[df_hr["rentals"].idxmax(), "hour"])
        _panel("panel-positive", "#15803d", "Rental Pattern Insight", [
            f"Busiest day: <strong>{peak_day}</strong> — focus promotions and ensure full stock availability on this day.",
            f"Peak hour: <strong>{peak_hour:02d}:00 – {peak_hour+1:02d}:00</strong> — ensure systems and staff are ready during this window.",
        ])
        _panel("panel-action", "#1d4ed8", "Recommended Actions", [
            f"<strong>Off-Peak Promotions:</strong> Run discounts on <strong>{slow_day}</strong> (slowest day) to distribute traffic more evenly across the week.",
            f"<strong>Peak Hour Readiness:</strong> Add support staff or automate return processing between <strong>{peak_hour:02d}:00</strong> and <strong>{peak_hour+1:02d}:00</strong>.",
        ])

        section_title("trend", "Average Rental Duration by Day of Week")
        chart_desc("Line chart showing how many days, on average, customers keep a film depending on the day they rented it. Helps identify if certain days are associated with longer holds that could reduce inventory availability.")
        fig_ad = px.line(
            df_dur, x="day_name", y="avg_days",
            markers=True,
            labels={"day_name": "Day", "avg_days": "Avg Days Kept"},
        )
        fig_ad.update_traces(line=dict(color=ORANGE, width=2.5), marker=dict(size=8, color=ORANGE))
        fig_ad.update_layout(**PL, height=280, yaxis=dict(gridcolor="#f0f1f8"))
        st.plotly_chart(fig_ad, use_container_width=True, config={"displayModeBar": False})

        section_title("pie", "Return Status Distribution")
        chart_desc("Donut chart breaking down all rentals into three outcomes: returned on time, returned late, or not yet returned. Provides a quick read on overall customer compliance.")
        status_colors = {"On Time": TEAL, "Late": RED, "Not Returned": ORANGE}
        fig_pie = px.pie(
            df_status, names="status", values="count",
            color="status", color_discrete_map=status_colors, hole=0.5,
        )
        fig_pie.update_traces(textposition="outside", textinfo="percent+label")
        fig_pie.update_layout(**PL, height=280, showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})

        on_time_pct = on_time / max(total_rentals, 1) * 100
        _panel("panel-positive" if on_time_pct >= 70 else "panel-negative",
               "#15803d" if on_time_pct >= 70 else "#b91c1c",
               "Return Status Insight", [
            f"<strong>{on_time_pct:.1f}% of rentals returned on time</strong> — ({on_time:,} of {int(total_rentals):,} transactions).",
            f"<strong>{late_pct:.1f}% returned late</strong> — {late_count:,} cases reducing inventory availability for other customers.",
            f"<strong>{not_ret} items</strong> have not been returned at all — these represent a direct asset loss.",
        ])

    # ── Tab 2 ─────────────────────────────────────────────────────────────────
    with tab2:
        section_title("warn", "Top 20 Customers with Most Late Returns")
        chart_desc("Identifies the customers responsible for the most late returns. Bar length shows number of incidents; color intensity reflects average days overdue. Use this to prioritize follow-up or apply additional rental restrictions.")
        fig_lc = px.bar(
            df_late_cust, x="late_returns", y="customer", orientation="h",
            color="avg_days_late", color_continuous_scale=["#fecb52", RED],
            labels={"late_returns": "Late Returns", "customer": "Customer",
                    "avg_days_late": "Avg Days Late"},
        )
        fig_lc.update_layout(**PL, height=500, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_lc, use_container_width=True, config={"displayModeBar": False})

        if not df_late_cust.empty:
            top_offender       = df_late_cust.iloc[0]["customer"]
            top_offender_count = int(df_late_cust.iloc[0]["late_returns"])
            top_offender_days  = float(df_late_cust.iloc[0]["avg_days_late"])
            repeat_offenders   = int((df_late_cust["late_returns"] >= 3).sum())

            _panel("panel-negative", "#b91c1c", "Late Return Findings", [
                f"Most frequent late returner: <strong>{top_offender}</strong> — {top_offender_count} incidents, averaging {top_offender_days:.1f} days overdue.",
                f"<strong>{repeat_offenders} customers</strong> have 3 or more late returns — these represent elevated operational risk.",
            ])
            _panel("panel-action", "#1d4ed8", "Recommended Actions", [
                f"<strong>Automated Reminders:</strong> Send SMS or email notifications 1 day before the due date — proven to reduce late returns by 30-40%.",
                f"<strong>Progressive Fines:</strong> Apply escalating late fees to incentivize timely returns.",
                f"<strong>Watchlist:</strong> Place the {repeat_offenders} repeat offenders on a watchlist — require a deposit or apply stricter rental terms.",
                f"<strong>Follow Up on Unreturned Items:</strong> Contact the {not_ret} customers with outstanding items directly — offer an extended rental option or damage settlement.",
            ])

        section_title("box", "Late Return Detail (Top 200)")
        chart_desc("Detailed table of the 200 most overdue rentals — showing the film, customer, allowed duration, and how many days late the return was.")
        if not df_late.empty:
            disp             = df_late[["title", "rating", "customer_name", "rental_duration",
                                        "actual_days", "days_late"]].copy()
            disp["actual_days"] = disp["actual_days"].round(1)
            disp["days_late"]   = disp["days_late"].round(1)
            disp.columns     = ["Film", "Rating", "Customer", "Allowed Days", "Actual Days", "Days Late"]
            st.dataframe(disp.reset_index(drop=True), use_container_width=True)

    # ── Tab 3 ─────────────────────────────────────────────────────────────────
    with tab3:
        section_title("trend", "Monthly Rental Volume")
        chart_desc("Bar chart showing total number of rentals per month across the entire dataset. Useful for identifying seasonal demand patterns, growth trends, or periods of decline.")
        fig_mo = go.Figure()
        fig_mo.add_trace(go.Bar(
            x=df_mo["month"], y=df_mo["rentals"],
            marker_color=PURPLE, opacity=0.85,
            hovertemplate="<b>%{x}</b><br>Rentals: %{y:,}<extra></extra>",
        ))
        fig_mo.update_layout(
            **PL, height=300,
            xaxis_title="Month", yaxis_title="Rentals",
            yaxis=dict(gridcolor="#f0f1f8"),
        )
        st.plotly_chart(fig_mo, use_container_width=True, config={"displayModeBar": False})

        peak_month = df_mo.loc[df_mo["rentals"].idxmax(), "month"]
        slow_month = df_mo.loc[df_mo["rentals"].idxmin(), "month"]
        _panel("panel-positive", "#15803d", "Monthly Trend Insight", [
            f"Peak rental month: <strong>{peak_month}</strong> — plan maximum stock availability and staffing ahead of this period.",
            f"Slowest month: <strong>{slow_month}</strong> — an opportunity to run promotional campaigns to lift activity during this low-demand window.",
        ])