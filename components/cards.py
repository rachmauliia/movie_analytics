"""
components/cards.py
Reusable HTML component helpers for all feature pages.
Icons are inline SVG — no emoji dependency.
"""

import streamlit as st


# ── SVG ICON LIBRARY ───────────────────────────────────────────────────────────
ICONS = {
    "dollar":   '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
    "film":     '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="17" y1="7" x2="22" y2="7"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="2" y1="17" x2="7" y2="17"/></svg>',
    "check":    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    "trend":    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
    "warn":     '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "star":     '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    "users":    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "clock":    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "bar":      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    "tag":      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
    "box":      '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>',
}

COLOR_MAP = {
    "purple": "#6c5ce7",
    "teal":   "#00b894",
    "orange": "#fd9644",
    "pink":   "#fd79a8",
    "blue":   "#0984e3",
    "red":    "#d63031",
}


def get_icon(name: str, color: str) -> str:
    c = COLOR_MAP.get(color, color)
    return ICONS.get(name, ICONS["bar"]).replace("{c}", c)


def kpi_card(label: str, value: str, sub: str, color: str, icon_name: str = "bar"):
    """Render a KPI card with SVG icon."""
    svg = get_icon(icon_name, color)
    st.markdown(f"""
        <div class="kpi-card {color}">
            <div class="kpi-icon-box {color}">{svg}</div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
    """, unsafe_allow_html=True)


def section_title(icon_name: str, title: str, color: str = "purple"):
    svg = get_icon(icon_name, color)
    st.markdown(f'<div class="section-title">{svg}&nbsp;{title}</div>', unsafe_allow_html=True)


def insight_box(text: str):
    st.markdown(f'<div class="insight-box">{text}</div>', unsafe_allow_html=True)


def page_header(title: str, subtitle: str, badge: str = ""):
    badge_html = f'<div class="header-badge">{badge}</div>' if badge else ""
    st.markdown(f"""
        <div class="page-header">
            <div>
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>
            {badge_html}
        </div>
    """, unsafe_allow_html=True)


def coming_soon(title: str, desc: str, icon_name: str = "bar", color: str = "purple"):
    svg = get_icon(icon_name, color)
    c = COLOR_MAP.get(color, "#6c5ce7")
    st.markdown(f"""
        <div class="cs-wrap">
            <div class="cs-icon-box" style="background:rgba({_hex_to_rgb(c)},0.10);">{svg}</div>
            <div class="cs-title">{title}</div>
            <div class="cs-desc">{desc}</div>
            <div class="cs-pill">Coming in the next update</div>
        </div>
    """, unsafe_allow_html=True)


def _hex_to_rgb(h: str) -> str:
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"