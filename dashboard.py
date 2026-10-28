
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="IPL Cricket Analytics",
    page_icon="🏏",
    layout="wide"
)

st.title("🏏 IPL Cricket Analytics Dashboard")
st.write("Explore IPL team performance and player statistics.")

# Load datasets
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR
@st.cache_data
def load_data():
    matches = pd.read_csv(DATA_DIR / "matches.csv")
    deliveries = pd.read_csv(DATA_DIR / "deliveries.csv")

    matches.columns = matches.columns.str.strip()
    deliveries.columns = deliveries.columns.str.strip()

    return matches, deliveries

try:
    matches, deliveries = load_data()
except Exception as e:
    st.error(f"Could not load the CSV files: {e}")
    st.info(
        "Make sure matches.csv and deliveries.csv "
        "are available inside the data folder."
    )
    st.stop()

# Detect common column names
def find_col(df, options):
    for col in options:
        if col in df.columns:
            return col
    return None

team1_col = find_col(matches, ["team1", "Team1"])
team2_col = find_col(matches, ["team2", "Team2"])
winner_col = find_col(matches, ["winner", "WinningTeam", "winner_team"])
season_col = find_col(matches, ["season", "Season"])
match_id_col = find_col(matches, ["id", "ID", "match_id"])

player_col = find_col(deliveries, ["batter", "batsman"])
runs_col = find_col(
    deliveries,
    ["batsman_run", "batsman_runs", "batter_runs"]
)
delivery_id_col = find_col(deliveries, ["ID", "id", "match_id"])

if not all([team1_col, team2_col, winner_col]):
    st.error("Could not identify team or winner columns in matches.csv.")
    st.write("Available match columns:", matches.columns.tolist())
    st.stop()

if not all([player_col, runs_col]):
    st.error("Could not identify player or runs columns in deliveries.csv.")
    st.write("Available delivery columns:", deliveries.columns.tolist())
    st.stop()

# Team win analysis
team_names = sorted(set(
    matches[team1_col].dropna().astype(str).tolist()
    + matches[team2_col].dropna().astype(str).tolist()
))

team_filter = st.selectbox("Filter by team", ["All Teams"] + team_names)

player_names = sorted(deliveries[player_col].dropna().astype(str).unique())
player_filter = st.selectbox(
    "Filter by player",
    ["All Players"] + player_names
)

valid_wins = matches[matches[winner_col].notna()]
team_wins = valid_wins[winner_col].value_counts().rename_axis("Team").reset_index(name="Wins")

team_matches = pd.concat([
    matches[[team1_col]].rename(columns={team1_col: "Team"}),
    matches[[team2_col]].rename(columns={team2_col: "Team"})
]).value_counts().rename("Matches Played").reset_index()

team_stats = team_matches.merge(team_wins, on="Team", how="left")
team_stats["Wins"] = team_stats["Wins"].fillna(0)
team_stats["Win Rate (%)"] = (
    team_stats["Wins"] / team_stats["Matches Played"] * 100
).round(2)

if team_filter != "All Teams":
    team_stats = team_stats[team_stats["Team"] == team_filter]

# Player runs
player_runs = (
    deliveries.groupby(player_col)[runs_col]
    .sum()
    .reset_index()
    .rename(columns={player_col: "Player", runs_col: "Runs"})
    .sort_values("Runs", ascending=False)
)

if player_filter != "All Players":
    player_runs = player_runs[player_runs["Player"] == player_filter]

# Match season trends
if season_col and match_id_col and delivery_id_col:
    season_lookup = matches[[match_id_col, season_col]].drop_duplicates()
    delivery_analysis = deliveries.merge(
        season_lookup,
        left_on=delivery_id_col,
        right_on=match_id_col,
        how="left",
        suffixes=("", "_match")
    )
    trend_season_col = season_col
else:
    delivery_analysis = deliveries.copy()
    trend_season_col = find_col(delivery_analysis, ["Season", "season"])

if trend_season_col:
    season_runs = (
        delivery_analysis.groupby(trend_season_col)[runs_col]
        .sum()
        .reset_index(name="Runs")
    )
else:
    season_runs = pd.DataFrame(columns=["Season", "Runs"])

# Summary cards
c1, c2, c3 = st.columns(3)

c1.metric("Matches", f"{len(matches):,}")
c2.metric("Teams", len(team_names))
c3.metric("Players", len(player_names))

st.subheader("Team Win Rate")
if not team_stats.empty:
    fig_team = px.bar(
        team_stats.sort_values("Win Rate (%)", ascending=False),
        x="Team",
        y="Win Rate (%)",
        title="Team Win Rate (%)",
        color="Win Rate (%)"
    )
    st.plotly_chart(fig_team, use_container_width=True)

st.subheader("Top Run Scorers")
if not player_runs.empty:
    top_players = player_runs.sort_values("Runs", ascending=False).head(15)
    fig_players = px.bar(
        top_players.sort_values("Runs"),
        x="Runs",
        y="Player",
        orientation="h",
        title="Top 15 Players by Batter Runs"
    )
    st.plotly_chart(fig_players, use_container_width=True)

st.subheader("Season-by-Season Runs")
if not season_runs.empty:
    fig_season = px.line(
        season_runs,
        x=trend_season_col,
        y="Runs",
        markers=True,
        title="Total Batter Runs by Season"
    )
    st.plotly_chart(fig_season, use_container_width=True)
else:
    st.warning("Season data was not detected in matches.csv.")

st.subheader("Team Statistics")
st.dataframe(team_stats, use_container_width=True)

st.caption(
    "Note: Statistics depend on the seasons and matches present in your dataset."
)
