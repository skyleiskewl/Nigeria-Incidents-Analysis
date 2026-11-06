import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Fatal Incidents in Nigeria", page_icon="📊", layout="wide")

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@st.cache_data
def load_data():
    df = pd.read_csv("incidents_clean.csv", parse_dates=["start", "end", "month"])
    df["month_name"] = df["month_num"].map(lambda m: MONTHS[m - 1])
    return df


df = load_data()

# ---------------------------------------------------------------- sidebar
st.sidebar.header("Filters")

years = sorted(df["year"].unique())
sel_years = st.sidebar.multiselect("Year", years, default=years)

zones = sorted(df["zone"].unique())
sel_zones = st.sidebar.multiselect("Geopolitical zone", zones, default=zones)

state_options = sorted(df.loc[df["zone"].isin(sel_zones), "state"].unique())
sel_states = st.sidebar.multiselect("State (leave empty for all)", state_options)

cats = sorted(df["category"].unique())
sel_cats = st.sidebar.multiselect("Incident category", cats, default=cats)

max_deaths = int(df["deaths"].max())
min_d, max_d = st.sidebar.slider("Deaths per incident", 1, max_deaths, (1, max_deaths))

st.sidebar.caption(
    "2022 starts on 17 June and 2026 ends on 14 July, so those are partial years. "
    "Only 2023-2025 are complete years."
)

mask = (
    df["year"].isin(sel_years)
    & df["zone"].isin(sel_zones)
    & df["category"].isin(sel_cats)
    & df["deaths"].between(min_d, max_d)
)
if sel_states:
    mask &= df["state"].isin(sel_states)
f = df[mask]

# ---------------------------------------------------------------- header
st.title("Fatal Incidents, Accidents and Violence in Nigeria")
st.caption(
    "Source: Kaggle, *Incidents, Accidents and Violence in Nigeria*. "
    "Each record is a reported fatal incident (at least one death). Cleaned and categorised in the project notebook."
)

if f.empty:
    st.warning("No incidents match the current filters. Widen the filters in the sidebar.")
    st.stop()

# ---------------------------------------------------------------- KPIs
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Fatal incidents", f"{len(f):,}")
k2.metric("Total deaths", f"{f['deaths'].sum():,}")
k3.metric("Mean deaths / incident", f"{f['deaths'].mean():.1f}")
k4.metric("Median deaths / incident", f"{f['deaths'].median():.0f}")
k5.metric("Deadliest incident", f"{f['deaths'].max():,}")

tab_over, tab_where, tab_when, tab_extreme, tab_data = st.tabs(
    ["Overview", "Where", "When", "Extreme events", "Data"]
)

# ---------------------------------------------------------------- overview
with tab_over:
    c1, c2 = st.columns(2)

    cat = (
        f.groupby("category")["deaths"]
        .agg(total_deaths="sum", incidents="count", median_deaths="median")
        .reset_index()
        .sort_values("total_deaths")
    )
    fig = px.bar(
        cat, x="total_deaths", y="category", orientation="h",
        hover_data=["incidents", "median_deaths"],
        title="Total deaths by incident category",
        labels={"total_deaths": "Total deaths", "category": ""},
        color_discrete_sequence=["#9d0208"],
    )
    c1.plotly_chart(fig, width="stretch")

    reg = f.groupby("zone")["deaths"].agg(total_deaths="sum", incidents="count").reset_index()
    fig = px.pie(
        reg, names="zone", values="total_deaths", hole=0.45,
        title="Share of deaths by zone",
    )
    c2.plotly_chart(fig, width="stretch")

    monthly = f.groupby("month")["deaths"].agg(incidents="count", total_deaths="sum").reset_index()
    fig = px.line(
        monthly, x="month", y=["total_deaths", "incidents"],
        title="Monthly trend", labels={"month": "", "value": "Count", "variable": ""},
    )
    st.plotly_chart(fig, width="stretch")
    st.caption("The first (June 2022) and last (July 2026) months are partial, so expect lower values at the ends.")

# ---------------------------------------------------------------- where
with tab_where:
    known = f[f["state"] != "Unknown"]
    st_stats = (
        known.groupby("state")["deaths"]
        .agg(incidents="count", total_deaths="sum", mean_deaths="mean", median_deaths="median")
        .reset_index()
    )

    metric = st.radio(
        "Rank states by",
        ["Total deaths", "Number of incidents", "Mean deaths per incident"],
        horizontal=True,
    )
    col = {"Total deaths": "total_deaths", "Number of incidents": "incidents",
           "Mean deaths per incident": "mean_deaths"}[metric]

    if col == "mean_deaths":
        min_inc = st.slider("Only include states with at least this many incidents", 1, 100, 30)
        pool = st_stats[st_stats["incidents"] >= min_inc]
    else:
        pool = st_stats

    top_n = st.slider("Number of states to show", 5, 37, 10)
    top = pool.nlargest(top_n, col).sort_values(col)
    if top.empty:
        st.info("No states meet that threshold under the current filters.")
    else:
        fig = px.bar(
            top, x=col, y="state", orientation="h",
            hover_data=["incidents", "total_deaths", "mean_deaths", "median_deaths"],
            title=f"Top {len(top)} states by {metric.lower()}",
            labels={col: metric, "state": ""},
            color_discrete_sequence=["#2a6f97"],
        )
        st.plotly_chart(fig, width="stretch")

    hs = known.groupby("state")["deaths"].sum().nlargest(12).index
    hc = known.groupby("category")["deaths"].sum().nlargest(8).index
    heat = (
        known[known["state"].isin(hs) & known["category"].isin(hc)]
        .pivot_table(index="state", columns="category", values="deaths", aggfunc="sum", fill_value=0)
    )
    if not heat.empty:
        heat = heat.loc[[s for s in hs if s in heat.index], [c for c in hc if c in heat.columns]]
        fig = px.imshow(
            heat, text_auto=",", aspect="auto", color_continuous_scale="YlOrRd",
            title="Deaths by state and category (top states and categories in the current selection)",
            labels={"color": "Deaths"},
        )
        st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- when
with tab_when:
    c1, c2 = st.columns(2)

    yr = f.groupby("year")["deaths"].agg(incidents="count", total_deaths="sum").reset_index()
    yr["year"] = yr["year"].astype(str)
    yr["status"] = yr["year"].map(lambda y: "Partial year" if y in ("2022", "2026") else "Complete year")
    fig = px.bar(
        yr, x="year", y="total_deaths", color="status", hover_data=["incidents"],
        title="Deaths by year",
        labels={"total_deaths": "Total deaths", "year": ""},
        color_discrete_map={"Complete year": "#9d0208", "Partial year": "#bbbbbb"},
    )
    c1.plotly_chart(fig, width="stretch")

    wd = f["weekday"].value_counts().reindex(WEEKDAYS).fillna(0).reset_index()
    wd.columns = ["weekday", "incidents"]
    fig = px.bar(
        wd, x="weekday", y="incidents", title="Incidents by day of week",
        labels={"weekday": "", "incidents": "Incidents"},
        color_discrete_sequence=["#e85d04"],
    )
    c2.plotly_chart(fig, width="stretch")

    ym = f.pivot_table(index="year", columns="month_name", values="deaths", aggfunc="sum")
    ym = ym.reindex(columns=[m for m in MONTHS if m in ym.columns])
    fig = px.imshow(
        ym, text_auto=",", aspect="auto", color_continuous_scale="Reds",
        title="Deaths by month and year (partial years show gaps or low values)",
        labels={"color": "Deaths", "x": "", "y": ""},
    )
    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- extreme events
with tab_extreme:
    n_mass = int((f["deaths"] >= 50).sum())
    share_mass = f.loc[f["deaths"] >= 50, "deaths"].sum() / f["deaths"].sum()
    st.markdown(
        f"**{n_mass:,} incidents ({n_mass / len(f):.1%}) with 50 or more deaths "
        f"account for {share_mass:.1%} of all deaths** in the current selection."
    )

    s = f["deaths"].sort_values(ascending=False).reset_index(drop=True)
    conc = pd.DataFrame({
        "Cumulative % of incidents": (s.index + 1) / len(s) * 100,
        "Cumulative % of deaths": s.cumsum() / s.sum() * 100,
    })
    fig = px.line(
        conc, x="Cumulative % of incidents", y="Cumulative % of deaths",
        title="Concentration of deaths (incidents ranked deadliest first)",
    )
    fig.add_shape(type="line", x0=0, y0=0, x1=100, y1=100, line=dict(dash="dash", color="grey"))
    st.plotly_chart(fig, width="stretch")

    st.subheader("Ten deadliest incidents in the current selection")
    st.dataframe(
        f.nlargest(10, "deaths")[["title", "start", "state", "category", "deaths"]]
        .assign(start=lambda d: d["start"].dt.date)
        .reset_index(drop=True),
        width="stretch",
    )

# ---------------------------------------------------------------- data
with tab_data:
    st.write(f"{len(f):,} rows match the current filters.")
    show = f[["id", "title", "start", "end", "deaths", "state", "zone", "category"]].copy()
    show["start"] = show["start"].dt.date
    show["end"] = show["end"].dt.date
    st.dataframe(show, width="stretch", height=450)
    st.download_button(
        "Download filtered data (CSV)",
        show.to_csv(index=False).encode("utf-8"),
        file_name="incidents_filtered.csv",
        mime="text/csv",
    )
