
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
from pathlib import Path

# Load datasets
BASE_DIR = Path(__file__).resolve().parent
matches = pd.read_csv(BASE_DIR / "data" / "matches.csv")
deliveries = pd.read_csv(BASE_DIR / "data" / "deliveries.csv")

# Find columns regardless of capitalization
def find_col(df, names):
    for name in names:
        for col in df.columns:
            if col.lower() == name.lower():
                return col
    return None

team1_col = find_col(matches, ["team1", "team_1"])
team2_col = find_col(matches, ["team2", "team_2"])
winner_col = find_col(matches, ["winningteam", "winner", "winning_team"])
season_col = find_col(matches, ["season", "year"])
match_id = find_col(matches, ["id", "match_id"])

player_col = find_col(deliveries, ["batter", "batsman"])
runs_col = find_col(deliveries, ["batsman_run", "batsman_runs", "batter_runs"])
batting_team_col = find_col(deliveries, ["battingteam", "batting_team"])
delivery_match_id = find_col(deliveries, ["id", "match_id"])

# Validate columns
if not all([team1_col, team2_col, winner_col, player_col, runs_col]):
    raise ValueError(
        "Required columns not found. Check your CSV column names."
    )

# Add season to deliveries if possible
if season_col and match_id and delivery_match_id:
    season_lookup = matches[[match_id, season_col]].drop_duplicates(match_id)
    deliveries = deliveries.merge(
        season_lookup,
        left_on=delivery_match_id,
        right_on=match_id,
        how="left",
        suffixes=("", "_match")
    )
    if season_col + "_match" in deliveries.columns:
        deliveries[season_col] = deliveries[season_col].fillna(
            deliveries[season_col + "_match"]
        )

teams = sorted(
    set(matches[team1_col].dropna().astype(str))
    | set(matches[team2_col].dropna().astype(str))
)
players = sorted(deliveries[player_col].dropna().astype(str).unique())

# Create Dash application
app = Dash(__name__)
app.title = "IPL Cricket Analytics"

app.layout = html.Div(
    style={"fontFamily": "Arial", "backgroundColor": "#f4f6f9",
           "padding": "25px"},
    children=[
        html.H1("IPL Cricket Analytics Dashboard",
                style={"textAlign": "center", "color": "#12345a"}),
        html.P("Explore IPL team and player performance",
               style={"textAlign": "center"}),

        html.Label("Select Team"),
        dcc.Dropdown(
            id="team-filter",
            options=[{"label": "All Teams", "value": "ALL"}] +
                    [{"label": t, "value": t} for t in teams],
            value="ALL", clearable=False
        ),

        html.Br(),
        html.Label("Select Player"),
        dcc.Dropdown(
            id="player-filter",
            options=[{"label": "All Players", "value": "ALL"}] +
                    [{"label": p, "value": p} for p in players],
            value="ALL", clearable=False
        ),

        html.Div(id="summary-cards",
                 style={"display": "flex", "gap": "15px",
                        "marginTop": "20px", "marginBottom": "20px"}),

        dcc.Graph(id="wins-chart"),
        dcc.Graph(id="players-chart"),
        dcc.Graph(id="season-chart")
    ]
)

@app.callback(
    Output("summary-cards", "children"),
    Output("wins-chart", "figure"),
    Output("players-chart", "figure"),
    Output("season-chart", "figure"),
    Input("team-filter", "value"),
    Input("player-filter", "value")
)
def update_dashboard(selected_team, selected_player):
    m = matches.copy()
    d = deliveries.copy()

    if selected_team != "ALL":
        m = m[
            (m[team1_col] == selected_team) |
            (m[team2_col] == selected_team)
        ]
        if batting_team_col:
            d = d[d[batting_team_col] == selected_team]

    if selected_player != "ALL":
        d = d[d[player_col] == selected_player]

    # Summary metrics
    total_matches = len(m)
    total_wins = (
        int((m[winner_col] == selected_team).sum())
        if selected_team != "ALL"
        else int(m[winner_col].notna().sum())
    )
    total_runs = int(d[runs_col].sum())

    card_style = {
        "backgroundColor": "white", "padding": "15px",
        "borderRadius": "8px", "flex": "1",
        "boxShadow": "0 1px 5px #ccc"
    }

    cards = [
        html.Div([html.H4("Matches"), html.H2(f"{total_matches:,}")],
                 style=card_style),
        html.Div([html.H4("Recorded Wins"), html.H2(f"{total_wins:,}")],
                 style=card_style),
        html.Div([html.H4("Batter Runs"), html.H2(f"{total_runs:,}")],
                 style=card_style)
    ]

    # Team wins
    wins = m[winner_col].dropna().value_counts().head(10)
    wins_df = wins.rename_axis("Team").reset_index(name="Wins")
    fig_wins = px.bar(
        wins_df, x="Wins", y="Team", orientation="h",
        title="Top Teams by Match Wins", template="plotly_white"
    )

    # Top players by runs
    top_players = (
        d.groupby(player_col)[runs_col].sum()
        .nlargest(10).sort_values()
        .rename("Runs").rename_axis("Player").reset_index()
    )
    fig_players = px.bar(
        top_players, x="Runs", y="Player", orientation="h",
        title="Top Players by Batter Runs", template="plotly_white"
    )

    # Season trend
    if season_col and season_col in d.columns:
        trend = d.groupby(season_col)[runs_col].sum().reset_index()
        trend = trend.sort_values(season_col)
        fig_season = px.line(
            trend, x=season_col, y=runs_col, markers=True,
            title="Batter Runs by IPL Season",
            labels={season_col: "Season", runs_col: "Batter Runs"},
            template="plotly_white"
        )
    else:
        fig_season = px.scatter(
            title="Season data unavailable",
            template="plotly_white"
        )

    return cards, fig_wins, fig_players, fig_season


if __name__ == "__main__":
    app.run(debug=True)
