#######################
# Import libraries
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
from pathlib import Path

#######################
# Page configuration
st.set_page_config(
    page_title="European Champions Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

alt.themes.enable("dark")

#######################
# CSS styling
st.markdown("""
<style>
[data-testid="block-container"] {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 1rem;
    padding-bottom: 0rem;
    margin-bottom: -7rem;
}
[data-testid="stVerticalBlock"] {
    padding-left: 0rem;
    padding-right: 0rem;
}
[data-testid="stMetric"] {
    background-color: #393939;
    text-align: center;
    padding: 15px 0;
}
[data-testid="stMetricLabel"] {
  display: flex;
  justify-content: center;
  align-items: center;
}
[data-testid="stMetricDeltaIcon-Up"] {
    position: relative;
    left: 38%;
    transform: translateX(-50%);
}
[data-testid="stMetricDeltaIcon-Down"] {
    position: relative;
    left: 38%;
    transform: translateX(-50%);
}
</style>
""", unsafe_allow_html=True)

#######################
# Load data
# CSV must have columns: country, year, state (club), region (league)
@st.cache_data(show_spinner=True)
def load_data():
    data_path = Path(__file__).parent / "data" / "/workspaces/population-dashboard/data/soccer_data.csv"
    if data_path.exists():
        return pd.read_csv(data_path)
    st.warning("soccer_data.csv not found in /data. Upload a CSV to proceed.")
    up = st.file_uploader("Upload soccer_data.csv", type="csv")
    if up is not None:
        return pd.read_csv(up)
    st.stop()

df_reshaped = load_data()
# Normalize column names (just in case)
df_reshaped.columns = [c.strip().lower() for c in df_reshaped.columns]
df_reshaped["year"] = pd.to_numeric(df_reshaped["year"], errors="coerce").astype("Int64")

#######################
# Sidebar
with st.sidebar:
    st.title('⚽ European Champions Dashboard')

    # Year selector
    year_list = sorted(df_reshaped.year.dropna().unique().tolist(), reverse=True)
    selected_year = st.selectbox('Select a year', year_list)

    # Color theme
    color_theme_list = ['blues', 'cividis', 'greens', 'inferno', 'magma',
                        'plasma', 'reds', 'rainbow', 'turbo', 'viridis']
    selected_color_theme = st.selectbox('Select a color theme', color_theme_list)

    # OPTIONAL: limit heatmap to top-N teams (by total titles across all seasons)
    team_counts = df_reshaped['state'].value_counts()
    max_teams = int(min(50, max(1, len(team_counts))))
    default_n = int(min(20, max_teams))
    top_n = st.slider('Top N teams for heatmap', 5, max_teams, default_n, step=1)
    top_teams = team_counts.head(top_n).index.tolist()

# Slices used below
df_selected_year = df_reshaped[df_reshaped.year == selected_year].copy()
df_selected_year_sorted = df_selected_year.sort_values(by="state", ascending=True)

#######################
# Plot helpers

# Heatmap (Year × Team) colored by count of champions
def make_heatmap(input_df, input_y, input_x, input_color, input_color_theme):
    heatmap = alt.Chart(input_df).mark_rect().encode(
        y=alt.Y(f'{input_y}:O',
                axis=alt.Axis(title="Year", titleFontSize=18,
                              titlePadding=15, titleFontWeight=900,
                              labelAngle=0)),
        x=alt.X(f'{input_x}:O',
                axis=alt.Axis(title="Team", titleFontSize=18,
                              titlePadding=15, titleFontWeight=900)),
        color=alt.Color(f'count({input_color}):Q',
                        legend=None,
                        scale=alt.Scale(scheme=input_color_theme)),
        stroke=alt.value('black'),
        strokeWidth=alt.value(0.25),
    ).properties(width=900).configure_axis(
        labelFontSize=12,
        titleFontSize=12
    )
    return heatmap

# Choropleth map (Europe)
def make_choropleth(input_df, input_color_theme):
    choropleth = px.choropleth(
        input_df,
        locations="country",
        locationmode="country names",
        color="titles",
        scope="europe",
        color_continuous_scale=input_color_theme,
        labels={"titles": "Titles"}
    )
    choropleth.update_layout(
        template='plotly_dark',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        margin=dict(l=0, r=0, t=0, b=0),
        height=350
    )
    return choropleth

#######################
# Dashboard Main Panel
col = st.columns((1.5, 4.5, 2), gap='medium')

with col[0]:
    st.markdown('#### Winners Tally (All Seasons)')
    winners = df_reshaped.groupby(["region", "state"], as_index=False)["year"].count()
    winners.rename(columns={"year": "titles"}, inplace=True)
    st.dataframe(
        winners.sort_values(["titles", "state"], ascending=[False, True]),
        use_container_width=True
    )

with col[1]:
    st.markdown('#### Titles by Country (Selected Year)')

    # Normalize country names so Plotly recognizes them
    country_fix = {
        "England": "United Kingdom",
        "UK": "United Kingdom",
        "Czech Republic": "Czechia",
        "Russia": "Russian Federation"
    }
    df_map_year = df_selected_year.copy()
    df_map_year["country"] = df_map_year["country"].replace(country_fix)

    # Group to titles per country for the selected year
    df_selected_year_grouped = (
        df_map_year.groupby("country", as_index=False)["state"].count()
                   .rename(columns={"state": "titles"})
    )

    if df_selected_year_grouped.empty:
        st.info("No data for the selected year.")
    else:
        choropleth = make_choropleth(df_selected_year_grouped, selected_color_theme)
        st.plotly_chart(choropleth, use_container_width=True)

    st.markdown('#### Champions Heatmap (Year × Team)')
    heatmap_df = df_reshaped[df_reshaped['state'].isin(top_teams)]
    heatmap = make_heatmap(heatmap_df, 'year', 'state', 'state', selected_color_theme)
    st.altair_chart(heatmap, use_container_width=True)

    st.markdown('#### Titles per Club (Last 5 Seasons)')
    df_titles = (
        df_reshaped.groupby(["state", "region"], as_index=False)["year"]
                   .count()
                   .rename(columns={"year": "titles"})
    )
    fig_titles = px.bar(
        df_titles.sort_values("titles"),
        y="state",
        x="titles",
        color="region",
        orientation="h",
        text="titles",
        labels={"state": "Champion Club", "titles": "Titles", "region": "League"},
        title="Titles per Club (Last 5 Seasons)"
    )
    fig_titles.update_layout(template="plotly_white", height=600, legend_title_text="League")
    fig_titles.update_traces(textposition="outside")
    st.plotly_chart(fig_titles, use_container_width=True)

with col[2]:
    st.markdown(f'#### Champions in {selected_year}')
    st.dataframe(
        df_selected_year_sorted,
        column_order=("state", "region"),
        hide_index=True,
        column_config={
            "state": st.column_config.TextColumn("Champion Club"),
            "region": st.column_config.TextColumn("League")
        }
    )

    with st.expander('About', expanded=True):
        st.write('''
        - Data: European football league champions (last 5 years)  
        - Leagues: Premier League, La Liga, Bundesliga, Serie A, Ligue 1  
        - Source: Wikipedia / official league records  
        ''')
