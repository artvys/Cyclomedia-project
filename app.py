# ============================================================
# Cyclomedia Pre-Collection Readiness Tool
# Streamlit Dashboard
# ============================================================

from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium


# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Cyclomedia Readiness Tool",
    page_icon="🗺️",
    layout="wide"
)


# ============================================================
# 2. PATHS
# ============================================================

OUTPUT_DIR = Path("outputs")

FINAL_AREAS_PATH = OUTPUT_DIR / "final_overdrive_scores.geojson"
GRID_PATH = OUTPUT_DIR / "local_issue_grid__centrum&noord_200m.geojson"
MARKERS_PATH = OUTPUT_DIR / "all_markers_cleaned.geojson"
AREA_SUMMARY_PATH = OUTPUT_DIR / "area_summary_table.csv"


# ============================================================
# 3. LOAD DATA
# ============================================================

@st.cache_data
def load_data():
    """
    Loads all dashboard layers.
    All spatial layers are converted to WGS84 for web mapping.
    """

    if not FINAL_AREAS_PATH.exists():
        raise FileNotFoundError(f"Missing file: {FINAL_AREAS_PATH}")

    if not GRID_PATH.exists():
        raise FileNotFoundError(f"Missing file: {GRID_PATH}")

    if not MARKERS_PATH.exists():
        raise FileNotFoundError(f"Missing file: {MARKERS_PATH}")

    areas = gpd.read_file(FINAL_AREAS_PATH).to_crs(epsg=4326)
    grid = gpd.read_file(GRID_PATH).to_crs(epsg=4326)
    markers = gpd.read_file(MARKERS_PATH).to_crs(epsg=4326)

    if AREA_SUMMARY_PATH.exists():
        area_summary = pd.read_csv(AREA_SUMMARY_PATH)
    else:
        area_summary = pd.DataFrame()

    return areas, grid, markers, area_summary


try:
    areas, grid, markers, area_summary = load_data()
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()


# ============================================================
# 4. HELPER FUNCTIONS
# ============================================================

def safe_col(df, col, default=None):
    """
    Returns a column if it exists, otherwise returns a default Series.
    """
    if col in df.columns:
        return df[col]
    return pd.Series([default] * len(df), index=df.index)


def format_score(value):
    """
    Formats numeric scores safely.
    """
    try:
        return f"{float(value):.3f}"
    except Exception:
        return "N/A"


def get_map_center(gdf):
    """
    Returns map center from a GeoDataFrame.
    """
    if gdf.empty:
        return [52.3676, 4.9041]  # Amsterdam fallback

    bounds = gdf.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    return [center_lat, center_lon]


def add_legend_to_map(map_object, title, color_dict):
    """
    Adds a simple HTML legend to a Folium map.
    """

    legend_items = ""

    for label, color in color_dict.items():
        legend_items += f"""
        <div style="
            display: flex;
            align-items: center;
            margin-bottom: 6px;
            color: #111111;
            font-size: 13px;
            font-family: Arial, sans-serif;
        ">
            <div style="
                width: 14px;
                height: 14px;
                background-color: {color};
                margin-right: 8px;
                border: 1px solid #555555;
                flex-shrink: 0;
            "></div>
            <span style="color: #111111;">{label}</span>
        </div>
        """

    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 30px;
        left: 30px;
        width: 290px;
        background-color: rgba(255, 255, 255, 0.95);
        z-index: 9999;
        border: 1px solid #999999;
        border-radius: 6px;
        padding: 12px;
        font-size: 13px;
        font-family: Arial, sans-serif;
        color: #111111;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.25);
    ">
        <div style="
            font-weight: bold;
            margin-bottom: 8px;
            color: #111111;
            font-size: 14px;
        ">
            {title}
        </div>
        {legend_items}
    </div>
    """

    map_object.get_root().html.add_child(folium.Element(legend_html))


# ============================================================
# 5. COLOR DICTIONARIES
# ============================================================

readiness_colors = {
    "Ready to collect": "#2a9d8f",
    "Operator warning": "#f4a261",
    "Pre-check required": "#e76f51",
    "Planned revisit candidate": "#d62828",
    "Structural difficulty": "#6a4c93",
    "Review route execution": "#457b9d",
    "Low evidence / monitor": "#adb5bd",
}

overdrive_category_colors = {
    "Priority Action": "#d62828",
    "Accept & Adapt": "#6a4c93",
    "Investigate Further": "#f4a261",
    "Monitor": "#2a9d8f",
}

marker_group_colors = {
    "Temporary Disruption": "#e76f51",
    "Operational Obstacle": "#f4a261",
    "Access / Structural Limitation": "#6a4c93",
    "Unclear / Other": "#adb5bd",
}


# ============================================================
# 6. HEADER
# ============================================================

st.title("Cyclomedia Pre-Collection Readiness Tool")

st.write(
    """
    This interactive prototype uses historical Cyclomedia data to support pre-collection planning.
    The goal is not to avoid difficult areas, but to help planners identify where collection may
    require pre-checking, operator warning, route review, or planned revisits.
    """
)

st.info(
    """
    **Important:** this prototype uses historical data as a risk baseline. In operational use,
    current roadworks, closures, events, or traffic data should be added before dispatch to confirm
    whether a historical risk is active now.
    """
)


# ============================================================
# 7. SIDEBAR CONTROLS
# ============================================================

st.sidebar.header("Dashboard controls")

available_areas = sorted(grid["area_name"].dropna().unique())

selected_area = st.sidebar.selectbox(
    "Select local inspection area",
    available_areas
)

readiness_options = sorted(grid["collection_readiness"].dropna().unique())

selected_readiness = st.sidebar.multiselect(
    "Filter collection readiness",
    readiness_options,
    default=readiness_options
)

priority_options = sorted(grid["revisit_priority_level"].dropna().astype(str).unique())

selected_priority = st.sidebar.multiselect(
    "Filter revisit priority level",
    priority_options,
    default=priority_options
)

show_markers = st.sidebar.checkbox(
    "Show operator markers",
    value=True
)

show_only_actionable = st.sidebar.checkbox(
    "Show only cells requiring attention",
    value=False
)

if show_only_actionable:
    selected_readiness = [
        "Operator warning",
        "Pre-check required",
        "Planned revisit candidate",
        "Structural difficulty",
        "Review route execution",
    ]


# ============================================================
# 8. FILTER DATA
# ============================================================

selected_grid = grid[
    (grid["area_name"] == selected_area)
    & (grid["collection_readiness"].isin(selected_readiness))
    & (grid["revisit_priority_level"].astype(str).isin(selected_priority))
].copy()

selected_markers = markers[markers["area_name"] == selected_area].copy()

selected_area_polygon = areas[areas["area_name"] == selected_area].copy()


# ============================================================
# 9. TABS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "1. Overview",
        "2. Local Readiness Map",
        "3. Priority Action List",
        "4. User Guide",
    ]
)


# ============================================================
# TAB 1 — OVERVIEW
# ============================================================

with tab1:
    st.subheader("Amsterdam project-area overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Project areas", len(areas))

    if "overdrive_risk_score" in areas.columns:
        top_area = areas.sort_values("overdrive_risk_score", ascending=False).iloc[0]
        col2.metric("Highest risk area", top_area["area_name"])
        col3.metric("Highest risk score", format_score(top_area["overdrive_risk_score"]))
    else:
        col2.metric("Highest risk area", "N/A")
        col3.metric("Highest risk score", "N/A")

    if "overdrive_planning_category" in areas.columns:
        priority_count = (areas["overdrive_planning_category"] == "Priority Action").sum()
        col4.metric("Priority action areas", int(priority_count))
    else:
        col4.metric("Priority action areas", "N/A")

    st.markdown("### Area ranking")

    overview_cols = [
        "area_name",
        "difficulty_score",
        "actionability_score",
        "structural_complexity_score",
        "overdrive_risk_score",
        "overdrive_risk_level",
        "overdrive_planning_category",
        "overdrive_recommendation",
    ]

    existing_overview_cols = [col for col in overview_cols if col in areas.columns]

    ranking_table = areas[existing_overview_cols].copy()

    if "overdrive_risk_score" in ranking_table.columns:
        ranking_table = ranking_table.sort_values("overdrive_risk_score", ascending=False)

    st.dataframe(ranking_table, use_container_width=True)

    if "overdrive_risk_score" in areas.columns and "overdrive_planning_category" in areas.columns:
        fig = px.bar(
            areas.sort_values("overdrive_risk_score", ascending=False),
            x="area_name",
            y="overdrive_risk_score",
            color="overdrive_planning_category",
            title="Overdrive-risk score by project area",
            labels={
                "area_name": "Project area",
                "overdrive_risk_score": "Overdrive-risk score",
                "overdrive_planning_category": "Planning category",
            },
            color_discrete_map=overdrive_category_colors,
        )

        fig.update_layout(
            xaxis_tickangle=-35,
            height=450,
            margin=dict(l=20, r=20, t=50, b=120),
        )

        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Overview map")

    overview_center = get_map_center(areas)

    overview_map = folium.Map(
        location=overview_center,
        zoom_start=11,
        tiles="CartoDB positron",
    )

    def style_area(feature):
        category = feature["properties"].get("overdrive_planning_category", "Monitor")

        return {
            "fillColor": overdrive_category_colors.get(category, "#cccccc"),
            "color": "#333333",
            "weight": 1,
            "fillOpacity": 0.55,
        }

    area_popup_fields = [
        "area_name",
        "difficulty_score",
        "actionability_score",
        "structural_complexity_score",
        "overdrive_risk_score",
        "overdrive_planning_category",
        "overdrive_recommendation",
    ]

    area_popup_fields = [f for f in area_popup_fields if f in areas.columns]

    folium.GeoJson(
        areas,
        name="Project areas",
        style_function=style_area,
        tooltip=folium.GeoJsonTooltip(
            fields=area_popup_fields,
            aliases=[field.replace("_", " ").title() for field in area_popup_fields],
            sticky=True,
        ),
    ).add_to(overview_map)

    add_legend_to_map(
        overview_map,
        "Planning category",
        overdrive_category_colors,
    )

    folium.LayerControl().add_to(overview_map)

    st_folium(overview_map, width=None, height=600)


# ============================================================
# TAB 2 — LOCAL READINESS MAP
# ============================================================

with tab2:
    st.subheader(f"Local collection readiness map: {selected_area}")

    if selected_grid.empty:
        st.warning("No grid cells match the current filters.")
    else:
        map_center = get_map_center(selected_grid)

        local_map = folium.Map(
            location=map_center,
            zoom_start=13,
            tiles="CartoDB positron",
        )

        if not selected_area_polygon.empty:
            folium.GeoJson(
                selected_area_polygon,
                name="Selected project boundary",
                style_function=lambda feature: {
                    "fillColor": "#ffffff00",
                    "color": "#000000",
                    "weight": 2,
                    "fillOpacity": 0,
                },
            ).add_to(local_map)

        def style_grid(feature):
            category = feature["properties"].get(
                "collection_readiness",
                "Low evidence / monitor",
            )

            return {
                "fillColor": readiness_colors.get(category, "#cccccc"),
                "color": "#333333",
                "weight": 0.4,
                "fillOpacity": 0.60,
            }

        grid_popup_fields = [
            "cell_id",
            "area_name",
            "collection_readiness",
            "dominant_issue_group",
            "marker_count",
            "recording_count",
            "marker_density",
            "recording_density",
            "revisit_priority_score",
            "revisit_priority_level",
            "revisit_cluster_id",
            "local_recommended_action",
        ]

        grid_popup_fields = [
            field for field in grid_popup_fields if field in selected_grid.columns
        ]

        folium.GeoJson(
            selected_grid,
            name="Local readiness grid",
            style_function=style_grid,
            tooltip=folium.GeoJsonTooltip(
                fields=grid_popup_fields,
                aliases=[field.replace("_", " ").title() for field in grid_popup_fields],
                sticky=True,
            ),
        ).add_to(local_map)

        if show_markers and not selected_markers.empty:
            for _, row in selected_markers.iterrows():
                marker_group = row.get("marker_group", "Unclear / Other")
                marker_type = row.get("type", "Unknown marker")

                color = marker_group_colors.get(marker_group, "#444444")

                folium.CircleMarker(
                    location=[row.geometry.y, row.geometry.x],
                    radius=3,
                    color=color,
                    fill=True,
                    fill_opacity=0.8,
                    popup=f"""
                    <b>Marker type:</b> {marker_type}<br>
                    <b>Group:</b> {marker_group}<br>
                    <b>Area:</b> {row.get("area_name", "")}
                    """,
                ).add_to(local_map)

        add_legend_to_map(
            local_map,
            "Collection readiness",
            readiness_colors,
        )

        folium.LayerControl().add_to(local_map)

        st_folium(local_map, width=None, height=650)

    st.markdown(
        """
        **Interpretation:**  
        The local grid translates historical collection issues into practical planning categories.
        It helps identify where collection can proceed normally, where operators should be warned,
        where current conditions should be checked, and where route execution may need review.
        """
    )


# ============================================================
# TAB 3 — PRIORITY ACTION LIST
# ============================================================

with tab3:
    st.subheader(f"Priority action list: {selected_area}")

    if selected_grid.empty:
        st.warning("No grid cells match the current filters.")
    else:
        action_cols = [
            "area_name",
            "cell_id",
            "collection_readiness",
            "dominant_issue_group",
            "marker_count",
            "recording_count",
            "marker_density",
            "recording_density",
            "revisit_priority_score",
            "revisit_priority_level",
            "revisit_cluster_id",
            "local_recommended_action",
        ]

        existing_action_cols = [
            col for col in action_cols if col in selected_grid.columns
        ]

        action_table = selected_grid[existing_action_cols].copy()

        if "revisit_priority_score" in action_table.columns:
            action_table = action_table.sort_values(
                "revisit_priority_score",
                ascending=False,
            )

        st.dataframe(action_table, use_container_width=True)

        csv = action_table.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download filtered action list as CSV",
            data=csv,
            file_name=f"{selected_area.replace(' ', '_')}_priority_action_list.csv",
            mime="text/csv",
        )

        st.markdown("### Readiness category distribution")

        readiness_counts = (
            selected_grid["collection_readiness"]
            .value_counts()
            .reset_index()
        )

        readiness_counts.columns = ["collection_readiness", "count"]

        fig_ready = px.bar(
            readiness_counts,
            x="collection_readiness",
            y="count",
            title="Local readiness categories",
            labels={
                "collection_readiness": "Collection readiness",
                "count": "Number of grid cells",
            },
            color="collection_readiness",
            color_discrete_map=readiness_colors,
        )

        fig_ready.update_layout(
            xaxis_tickangle=-35,
            showlegend=False,
            height=420,
            margin=dict(l=20, r=20, t=50, b=120),
        )

        st.plotly_chart(fig_ready, use_container_width=True)

        st.markdown("### Dominant issue group distribution")

        if "dominant_issue_group" in selected_grid.columns:
            issue_counts = (
                selected_grid["dominant_issue_group"]
                .value_counts()
                .reset_index()
            )

            issue_counts.columns = ["dominant_issue_group", "count"]

            fig_issue = px.bar(
                issue_counts,
                x="dominant_issue_group",
                y="count",
                title="Dominant issue groups",
                labels={
                    "dominant_issue_group": "Dominant issue group",
                    "count": "Number of grid cells",
                },
            )

            fig_issue.update_layout(
                xaxis_tickangle=-35,
                height=420,
                margin=dict(l=20, r=20, t=50, b=120),
            )

            st.plotly_chart(fig_issue, use_container_width=True)


# ============================================================
# TAB 4 — USER GUIDE
# ============================================================

with tab4:
    st.subheader("How to use this tool")

    st.markdown(
        """
        ### Purpose

        This dashboard is a **pre-collection planning prototype** for Cyclomedia.
        It uses historical operational data to identify zones where future collection may require
        extra preparation.

        The tool does **not** replace route optimization. Instead, it provides a readiness and
        revisit-risk layer that can support planning before vehicles are sent out.

        ---

        ### Suggested workflow

        1. Start with the **Overview** tab to see which Amsterdam project areas have higher
           overdrive-risk.
        2. Select a project area in the sidebar, such as **Amsterdam Centrum** or **Amsterdam Noord**.
        3. Open the **Local Readiness Map** to inspect grid cells inside the selected area.
        4. Use sidebar filters to focus on categories such as **Pre-check required**,
           **Operator warning**, or **Review route execution**.
        5. Open the **Priority Action List** to see recommended actions for specific grid cells.
        6. Download the filtered action list if it should be shared with planners or operators.

        ---

        ### Score interpretation

        **Difficulty score**  
        Measures how problematic a project area appears based on markers, recording activity,
        and DRMS-related quality signals.

        **Actionability score**  
        Estimates whether the difficulty appears manageable through planning. Temporary
        disruptions and operational obstacles are treated as more actionable than purely
        structural limitations.

        **Structural complexity score**  
        Measures how much difficulty may come from the road network itself, using indicators
        such as road density, intersection density, dead-end ratio, one-way share, and segment
        structure.

        **Overdrive-risk score**  
        Combines difficulty, actionability, and structural complexity into one planning indicator.

        **Collection readiness**  
        Converts analytical signals into practical categories for local grid cells.

        ---

        ### Collection readiness categories

        **Ready to collect**  
        No strong historical risk signal. Include in normal collection.

        **Operator warning**  
        Historical obstacle or local barrier risk. Brief the operator before entering.

        **Pre-check required**  
        Temporary disruption risk. Check current construction, closures, or events before collection.

        **Planned revisit candidate**  
        If current disruption is confirmed, group this cell with nearby risky cells for a planned revisit.

        **Structural difficulty**  
        Difficulty is likely linked to access or road network structure. Plan extra time or
        an experienced operator.

        **Review route execution**  
        High recording activity with limited marker evidence. Review whether repeated effort
        or inefficient execution may have occurred.

        **Low evidence / monitor**  
        Too little evidence for strong action. Monitor unless newer data confirms a problem.

        ---

        ### Limitations

        This prototype currently uses **historical Cyclomedia data** as a risk baseline.
        It does not yet include live roadworks, traffic, closures, or event data.

        For real operational use, current condition data should be added before collection.
        The best practical workflow would be:

        **historical risk baseline + current disruption layer = collection planning priority**

        The overdrive-risk score should be interpreted as a planning-support indicator, not as
        Cyclomedia's official net overdrive metric.
        """
    )


# ============================================================
# FOOTER
# ============================================================

st.caption(
    "Cyclomedia project prototype — historical data used as risk baseline; current-condition integration recommended for operational use."
)