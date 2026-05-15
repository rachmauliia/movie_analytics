"""
Movie Analytics Dashboard - Flask Backend
app.py

Endpoints:
  /api/overview           -> KPI summary
  /api/monthly_revenue    -> monthly trend
  /api/top_films          -> top 5 films by revenue
  /api/revenue_by_rating  -> revenue grouped by rating
  /api/top_genres         -> top N genres by revenue
  /api/film_table         -> all films for content table
  /api/dead_stock         -> dead stock analysis
  /api/rental_behavior    -> late returns + day + duration + store
  /api/actors             -> actor leaderboard
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import psycopg2.extras

app = Flask(__name__)
CORS(app)  # allow calls from the HTML file

# -----------------------------------------
# DATABASE CONFIG
# -----------------------------------------
DB_CONFIG = dict(
    host="localhost",
    database="dvdrental",
    user="postgres",
    password="your password",
    port=5432,
)


def get_conn():
    """Return a fresh connection (safer than reusing one global conn)."""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


def query(sql, params=None):
    """Run a SELECT and return list of dicts."""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def query_one(sql, params=None):
    rows = query(sql, params)
    return rows[0] if rows else {}


def to_float(x):
    return float(x) if x is not None else 0.0


# -----------------------------------------
# OVERVIEW
# -----------------------------------------
@app.route("/api/overview")
def overview():
    total_revenue = to_float(query_one("SELECT SUM(amount) AS v FROM payment")["v"])
    total_rentals  = query_one("SELECT COUNT(*) AS v FROM rental")["v"]
    total_films    = query_one("SELECT COUNT(*) AS v FROM film")["v"]
    active_customers = query_one(
        "SELECT COUNT(DISTINCT customer_id) AS v FROM rental"
    )["v"]

    avg_per_rental = total_revenue / total_rentals if total_rentals else 0
    avg_per_film   = total_revenue / total_films   if total_films   else 0

    dead_stock = query_one("""
        SELECT COUNT(*) AS v
        FROM film f
        LEFT JOIN inventory i ON f.film_id = i.film_id
        LEFT JOIN rental r    ON i.inventory_id = r.inventory_id
        WHERE r.rental_id IS NULL
    """)["v"]

    return jsonify({
        "total_revenue":    round(total_revenue, 2),
        "total_rentals":    int(total_rentals),
        "total_films":      int(total_films),
        "active_customers": int(active_customers),
        "avg_per_rental":   round(avg_per_rental, 2),
        "avg_per_film":     round(avg_per_film, 2),
        "dead_stock":       int(dead_stock),
    })


# -----------------------------------------
# MONTHLY REVENUE
# -----------------------------------------
@app.route("/api/monthly_revenue")
def monthly_revenue():
    rows = query("""
        SELECT TO_CHAR(payment_date, 'YYYY-MM') AS month,
               ROUND(SUM(amount)::numeric, 2)   AS revenue
        FROM payment
        GROUP BY 1
        ORDER BY 1
    """)
    return jsonify([{"month": r["month"], "revenue": to_float(r["revenue"])} for r in rows])


# -----------------------------------------
# TOP FILMS
# -----------------------------------------
@app.route("/api/top_films")
def top_films():
    limit = int(request.args.get("limit", 5))
    rows = query("""
        SELECT f.title,
               COUNT(r.rental_id)                     AS rentals,
               ROUND(COALESCE(SUM(p.amount),0)::numeric, 2) AS revenue
        FROM film f
        JOIN inventory i ON f.film_id      = i.film_id
        JOIN rental r    ON i.inventory_id = r.inventory_id
        LEFT JOIN payment p ON r.rental_id = p.rental_id
        GROUP BY f.title
        ORDER BY revenue DESC
        LIMIT %s
    """, (limit,))
    return jsonify([
        {"title": r["title"], "rentals": int(r["rentals"]), "revenue": to_float(r["revenue"])}
        for r in rows
    ])


# -----------------------------------------
# REVENUE BY RATING
# -----------------------------------------
@app.route("/api/revenue_by_rating")
def revenue_by_rating():
    rows = query("""
        SELECT f.rating::text                               AS rating,
               COUNT(r.rental_id)                          AS rentals,
               ROUND(COALESCE(SUM(p.amount),0)::numeric,2) AS revenue
        FROM film f
        LEFT JOIN inventory i ON f.film_id      = i.film_id
        LEFT JOIN rental r    ON i.inventory_id = r.inventory_id
        LEFT JOIN payment p   ON r.rental_id    = p.rental_id
        GROUP BY f.rating
        ORDER BY revenue DESC
    """)
    return jsonify([
        {"rating": r["rating"], "rentals": int(r["rentals"]), "revenue": to_float(r["revenue"])}
        for r in rows
    ])


# -----------------------------------------
# TOP GENRES
# -----------------------------------------
@app.route("/api/top_genres")
def top_genres():
    limit = int(request.args.get("limit", 10))
    rows = query("""
        SELECT c.name                                       AS category,
               COUNT(r.rental_id)                          AS rentals,
               ROUND(COALESCE(SUM(p.amount),0)::numeric,2) AS revenue
        FROM category c
        JOIN film_category fc ON c.category_id  = fc.category_id
        JOIN film f           ON fc.film_id      = f.film_id
        LEFT JOIN inventory i ON f.film_id       = i.film_id
        LEFT JOIN rental r    ON i.inventory_id  = r.inventory_id
        LEFT JOIN payment p   ON r.rental_id     = p.rental_id
        GROUP BY c.name
        ORDER BY revenue DESC
        LIMIT %s
    """, (limit,))
    return jsonify([
        {"category": r["category"], "rentals": int(r["rentals"]), "revenue": to_float(r["revenue"])}
        for r in rows
    ])


# -----------------------------------------
# FILM TABLE (Content Performance)
# -----------------------------------------
@app.route("/api/film_table")
def film_table():
    rows = query("""
        SELECT f.title,
               f.rating::text                              AS rating,
               COUNT(r.rental_id)                         AS rentals,
               ROUND(COALESCE(SUM(p.amount),0)::numeric,2) AS revenue
        FROM film f
        LEFT JOIN inventory i ON f.film_id      = i.film_id
        LEFT JOIN rental r    ON i.inventory_id = r.inventory_id
        LEFT JOIN payment p   ON r.rental_id    = p.rental_id
        GROUP BY f.title, f.rating
        ORDER BY revenue DESC
    """)
    return jsonify([
        {
            "title":   r["title"],
            "rating":  r["rating"],
            "rentals": int(r["rentals"]),
            "revenue": to_float(r["revenue"]),
        }
        for r in rows
    ])


# -----------------------------------------
# DEAD STOCK
# -----------------------------------------
@app.route("/api/dead_stock")
def dead_stock_detail():
    rented = query_one("""
        SELECT COUNT(DISTINCT f.film_id) AS v
        FROM film f
        JOIN inventory i ON f.film_id      = i.film_id
        JOIN rental r    ON i.inventory_id = r.inventory_id
    """)["v"]

    by_rating = query("""
        SELECT f.rating::text AS rating, COUNT(*) AS count
        FROM film f
        LEFT JOIN inventory i ON f.film_id      = i.film_id
        LEFT JOIN rental r    ON i.inventory_id = r.inventory_id
        WHERE r.rental_id IS NULL
        GROUP BY f.rating
        ORDER BY count DESC
    """)

    return jsonify({
        "rented":    int(rented),
        "by_rating": [{"rating": r["rating"], "count": int(r["count"])} for r in by_rating],
    })


# -----------------------------------------
# RENTAL BEHAVIOR
# -----------------------------------------
@app.route("/api/rental_behavior")
def rental_behavior():
    # Late returns (only completed rentals that have a return_date)
    late_row = query_one("""
        SELECT
            COUNT(*) FILTER (WHERE return_date > rental_date + INTERVAL '1 day' * (
                SELECT rental_duration FROM film f
                JOIN inventory i ON f.film_id = i.film_id
                WHERE i.inventory_id = r.inventory_id
                LIMIT 1
            )) AS late,
            COUNT(*) AS total
        FROM rental r
        WHERE return_date IS NOT NULL
    """)

    # Rentals by day of week
    days = query("""
        SELECT TO_CHAR(rental_date, 'Dy') AS day,
               COUNT(*) AS rentals
        FROM rental
        GROUP BY day
        ORDER BY MIN(EXTRACT(DOW FROM rental_date))
    """)

    # Rental duration distribution
    duration = query("""
        SELECT
            LEAST(EXTRACT(DAY FROM (return_date - rental_date))::int, 8) AS days,
            COUNT(*) AS rentals
        FROM rental
        WHERE return_date IS NOT NULL
        GROUP BY 1
        ORDER BY 1
    """)

    # Late returns by store
    store_late = query("""
        SELECT
            i.store_id,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE r.return_date > r.rental_date + INTERVAL '1 day' * (
                SELECT f2.rental_duration FROM film f2
                JOIN inventory i2 ON f2.film_id = i2.film_id
                WHERE i2.inventory_id = r.inventory_id
                LIMIT 1
            )) AS late
        FROM rental r
        JOIN inventory i ON r.inventory_id = i.inventory_id
        WHERE r.return_date IS NOT NULL
        GROUP BY i.store_id
        ORDER BY i.store_id
    """)

    store_late_out = []
    for s in store_late:
        t = int(s["total"])
        l = int(s["late"]) if s["late"] else 0
        rate = round(l / t * 100, 1) if t else 0
        store_late_out.append({"store_id": s["store_id"], "total": t, "late": l, "rate": rate})

    return jsonify({
        "late": {"late": int(late_row.get("late") or 0), "total": int(late_row.get("total") or 0)},
        "days": [{"day": r["day"], "rentals": int(r["rentals"])} for r in days],
        "duration": [{"days": int(r["days"]), "rentals": int(r["rentals"])} for r in duration],
        "store_late": store_late_out,
    })


# -----------------------------------------
# ACTORS
# -----------------------------------------
@app.route("/api/actors")
def actors():
    limit = int(request.args.get("limit", 20))
    rows = query("""
        SELECT
            a.first_name || ' ' || a.last_name             AS name,
            COUNT(DISTINCT fa.film_id)                      AS films,
            COUNT(r.rental_id)                              AS rentals,
            ROUND(COALESCE(SUM(p.amount),0)::numeric, 2)   AS revenue
        FROM actor a
        JOIN film_actor fa  ON a.actor_id     = fa.actor_id
        JOIN film f         ON fa.film_id     = f.film_id
        LEFT JOIN inventory i ON f.film_id    = i.film_id
        LEFT JOIN rental r    ON i.inventory_id = r.inventory_id
        LEFT JOIN payment p   ON r.rental_id  = p.rental_id
        GROUP BY a.actor_id, a.first_name, a.last_name
        ORDER BY revenue DESC
        LIMIT %s
    """, (limit,))
    return jsonify([
        {
            "name":    r["name"],
            "films":   int(r["films"]),
            "rentals": int(r["rentals"]),
            "revenue": to_float(r["revenue"]),
        }
        for r in rows
    ])


# -----------------------------------------
# RENTAL TRENDS (monthly rental count — for overview dual-view)
# -----------------------------------------
@app.route("/api/rental_trends")
def rental_trends():
    rows = query("""
        SELECT TO_CHAR(rental_date, 'YYYY-MM') AS month,
               COUNT(*) AS rentals
        FROM rental
        GROUP BY 1
        ORDER BY 1
    """)
    return jsonify([{"month": r["month"], "rentals": int(r["rentals"])} for r in rows])


# -----------------------------------------
# TIME SERIES ANALYSIS (combined revenue + rentals per month)
# -----------------------------------------
@app.route("/api/time_series_analysis")
def time_series_analysis():
    rows = query("""
        SELECT
            TO_CHAR(p.payment_date, 'YYYY-MM')          AS period,
            ROUND(SUM(p.amount)::numeric, 2)             AS revenue,
            COUNT(DISTINCT r.rental_id)                  AS rentals,
            COUNT(DISTINCT p.customer_id)                AS customers
        FROM payment p
        JOIN rental r ON p.rental_id = r.rental_id
        GROUP BY 1
        ORDER BY 1
    """)
    return jsonify([
        {
            "period":    r["period"],
            "revenue":   to_float(r["revenue"]),
            "rentals":   int(r["rentals"]),
            "customers": int(r["customers"]),
        }
        for r in rows
    ])


# -----------------------------------------
# REVENUE GROWTH (month-over-month % growth)
# -----------------------------------------
@app.route("/api/revenue_growth")
def revenue_growth():
    rows = query("""
        WITH monthly AS (
            SELECT TO_CHAR(payment_date, 'YYYY-MM') AS month,
                   ROUND(SUM(amount)::numeric, 2)   AS revenue
            FROM payment
            GROUP BY 1
            ORDER BY 1
        )
        SELECT
            month,
            revenue,
            LAG(revenue) OVER (ORDER BY month) AS prev_revenue,
            CASE
                WHEN LAG(revenue) OVER (ORDER BY month) IS NULL THEN NULL
                WHEN LAG(revenue) OVER (ORDER BY month) = 0     THEN NULL
                ELSE ROUND(
                    ((revenue - LAG(revenue) OVER (ORDER BY month))
                     / LAG(revenue) OVER (ORDER BY month) * 100)::numeric, 1)
            END AS growth_pct
        FROM monthly
    """)
    return jsonify([
        {
            "month":       r["month"],
            "revenue":     to_float(r["revenue"]),
            "prev_revenue":to_float(r["prev_revenue"]) if r["prev_revenue"] else None,
            "growth_pct":  float(r["growth_pct"]) if r["growth_pct"] is not None else None,
        }
        for r in rows
    ])


# -----------------------------------------
# SEASONAL DEMAND (aggregate rentals by calendar month 1-12)
# -----------------------------------------
@app.route("/api/seasonal_demand")
def seasonal_demand():
    rows = query("""
        SELECT
            TO_CHAR(DATE_TRUNC('month', rental_date), 'Mon') AS month,
            EXTRACT(MONTH FROM rental_date)::int              AS month_num,
            COUNT(*)                                          AS rentals
        FROM rental
        GROUP BY month, month_num
        ORDER BY month_num
    """)
    if not rows:
        return jsonify([])
    avg_rentals = sum(r["rentals"] for r in rows) / len(rows)
    return jsonify([
        {
            "month":   r["month"],
            "rentals": int(r["rentals"]),
            "avg":     round(avg_rentals, 1),
        }
        for r in rows
    ])


# -----------------------------------------
# CUSTOMER BEHAVIOR (unique active customers per month)
# -----------------------------------------
@app.route("/api/customer_behavior")
def customer_behavior():
    rows = query("""
        SELECT TO_CHAR(rental_date, 'YYYY-MM') AS month,
               COUNT(DISTINCT customer_id)     AS active_customers
        FROM rental
        GROUP BY 1
        ORDER BY 1
    """)
    return jsonify([
        {"month": r["month"], "active_customers": int(r["active_customers"])}
        for r in rows
    ])


# -----------------------------------------
# GENRE TRENDS (top 5 genres, monthly rental counts — pivot-style)
# -----------------------------------------
@app.route("/api/genre_trends")
def genre_trends():
    # Get top 5 genres by total rentals
    top_genres = query("""
        SELECT c.name AS genre
        FROM category c
        JOIN film_category fc ON c.category_id = fc.category_id
        JOIN film f           ON fc.film_id     = f.film_id
        LEFT JOIN inventory i ON f.film_id      = i.film_id
        LEFT JOIN rental r    ON i.inventory_id = r.inventory_id
        GROUP BY c.name
        ORDER BY COUNT(r.rental_id) DESC
        LIMIT 5
    """)
    genre_names = [g["genre"] for g in top_genres]

    # Monthly counts per genre
    raw = query("""
        SELECT TO_CHAR(r.rental_date, 'YYYY-MM') AS month,
               c.name AS genre,
               COUNT(r.rental_id) AS rentals
        FROM rental r
        JOIN inventory i      ON r.inventory_id  = i.inventory_id
        JOIN film f           ON i.film_id        = f.film_id
        JOIN film_category fc ON f.film_id        = fc.film_id
        JOIN category c       ON fc.category_id  = c.category_id
        WHERE c.name = ANY(%s)
        GROUP BY 1, 2
        ORDER BY 1
    """, (genre_names,))

    # Pivot into {month, Genre1: N, Genre2: N, ...}
    from collections import defaultdict
    month_map = defaultdict(lambda: {g: 0 for g in genre_names})
    for r in raw:
        month_map[r["month"]][r["genre"]] = int(r["rentals"])

    data = [{"month": m, **counts} for m, counts in sorted(month_map.items())]
    return jsonify({"genres": genre_names, "data": data})


# -----------------------------------------
# COMPLEX CUSTOMER QUERY
# /api/customer_query?min_cost=100&sort=cost&limit=50
# Returns customers whose total rental spend >= min_cost
# -----------------------------------------
@app.route("/api/customer_query")
def customer_query():
    min_cost  = float(request.args.get("min_cost", 0))
    sort_by   = request.args.get("sort", "cost")   # cost | rentals | name
    limit     = int(request.args.get("limit", 100))

    sort_col  = {
        "cost":    "total_cost DESC",
        "rentals": "total_rentals DESC",
        "name":    "customer_name ASC",
    }.get(sort_by, "total_cost DESC")

    rows = query(f"""
        SELECT
            c.customer_id,
            c.first_name || ' ' || c.last_name              AS customer_name,
            c.email,
            ci.city,
            co.country,
            COUNT(DISTINCT r.rental_id)                      AS total_rentals,
            ROUND(COALESCE(SUM(p.amount), 0)::numeric, 2)   AS total_cost,
            MAX(r.rental_date)                               AS last_rental
        FROM customer c
        JOIN address a   ON c.address_id   = a.address_id
        JOIN city ci     ON a.city_id      = ci.city_id
        JOIN country co  ON ci.country_id  = co.country_id
        LEFT JOIN rental r    ON c.customer_id = r.customer_id
        LEFT JOIN payment p   ON r.rental_id   = p.rental_id
        GROUP BY c.customer_id, c.first_name, c.last_name, c.email, ci.city, co.country
        HAVING ROUND(COALESCE(SUM(p.amount), 0)::numeric, 2) >= %s
        ORDER BY {sort_col}
        LIMIT %s
    """, (min_cost, limit))

    return jsonify([
        {
            "customer_id":   r["customer_id"],
            "customer_name": r["customer_name"],
            "email":         r["email"],
            "city":          r["city"],
            "country":       r["country"],
            "total_rentals": int(r["total_rentals"]),
            "total_cost":    to_float(r["total_cost"]),
            "last_rental":   str(r["last_rental"])[:10] if r["last_rental"] else "-",
        }
        for r in rows
    ])


# -----------------------------------------
# MONTHLY REVENUE EXTENDED (for prediction)
# /api/monthly_revenue_extended
# Returns monthly revenue + basic stats for frontend ML
# -----------------------------------------
@app.route("/api/monthly_revenue_extended")
def monthly_revenue_extended():
    rows = query("""
        SELECT TO_CHAR(payment_date, 'YYYY-MM') AS month,
               ROUND(SUM(amount)::numeric, 2)   AS revenue,
               COUNT(*)                          AS transactions,
               COUNT(DISTINCT customer_id)       AS unique_customers
        FROM payment
        GROUP BY 1
        ORDER BY 1
    """)
    return jsonify([
        {
            "month":            r["month"],
            "revenue":          to_float(r["revenue"]),
            "transactions":     int(r["transactions"]),
            "unique_customers": int(r["unique_customers"]),
        }
        for r in rows
    ])


# -----------------------------------------
# RUN
# -----------------------------------------
if __name__ == "__main__":
    print("Movie Analytics API starting on http://localhost:5000")
    print("Endpoints:")
    endpoints = [
        "/api/overview", "/api/monthly_revenue", "/api/rental_trends",
        "/api/top_films", "/api/revenue_by_rating", "/api/top_genres",
        "/api/film_table", "/api/dead_stock", "/api/rental_behavior", "/api/actors",
        "/api/time_series_analysis", "/api/revenue_growth", "/api/seasonal_demand",
        "/api/customer_behavior", "/api/genre_trends",
        "/api/customer_query", "/api/monthly_revenue_extended",
    ]
    for ep in endpoints:
        print(f"  {ep}")
    app.run(debug=True, port=5000)