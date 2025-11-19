from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import random
from config import Config
from llama_client import LlamaClient
import secrets

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Llama clients
topic_generator = LlamaClient(app.config["LLAMA_TOPIC_IP"])
judge = LlamaClient(app.config["LLAMA_JUDGE_IP"])

# Game state storage (in production, use database)
games = {}


def get_or_create_game(game_id):
    """Get existing game or create new one"""
    if game_id not in games:
        games[game_id] = {
            "players": {},
            "current_round": 0,
            "max_rounds": app.config["MAX_ROUNDS"],
            "current_topic": None,
            "selected_topics": None,
            "topic_chooser": None,
            "phase": "lobby",  # lobby, topic_selection, planning, results, game_over
            "round_results": [],
        }
    return games[game_id]


@app.route("/")
def index():
    """Main landing page"""
    return render_template("index.html")


@app.route("/create_game", methods=["POST"])
def create_game():
    """Create a new game"""
    game_id = secrets.token_urlsafe(3)
    get_or_create_game(game_id)
    return jsonify({"game_id": game_id})


@app.route("/game/<game_id>")
def game(game_id):
    """Game page"""
    if game_id not in games:
        return redirect(url_for("index"))

    player_name = request.args.get("player_name", "")
    return render_template("game.html", game_id=game_id, player_name=player_name)


@app.route("/api/game/<game_id>/join", methods=["POST"])
def join_game(game_id):
    """Join a game"""
    data = request.json
    player_name = data.get("player_name", "").strip()

    if not player_name:
        return jsonify({"error": "Player name required"}), 400

    game = get_or_create_game(game_id)

    if player_name not in game["players"]:
        game["players"][player_name] = {
            "survival_count": 0,
            "death_count": 0,
            "current_plan": None,
            "ready": False,
        }

    return jsonify({"success": True, "players": list(game["players"].keys())})


@app.route("/api/game/<game_id>/start", methods=["POST"])
def start_game(game_id):
    """Start the game"""
    game = get_or_create_game(game_id)

    if len(game["players"]) < 2:
        return jsonify({"error": "Need at least 2 players"}), 400

    game["current_round"] = 1
    game["phase"] = "topic_selection"

    # Choose random player to select topic
    game["topic_chooser"] = random.choice(list(game["players"].keys()))

    # Generate topics
    game["selected_topics"] = topic_generator.generate_topics()

    return jsonify(
        {
            "success": True,
            "topic_chooser": game["topic_chooser"],
            "topics": game["selected_topics"],
        }
    )


@app.route("/api/game/<game_id>/select_topic", methods=["POST"])
def select_topic(game_id):
    """Select a topic for the round"""
    data = request.json
    topic_index = data.get("topic_index")
    custom_topic = data.get("custom_topic")
    player_name = data.get("player_name")

    game = get_or_create_game(game_id)

    if player_name != game["topic_chooser"]:
        return jsonify({"error": "Not your turn to choose"}), 403
    # If chooser provided a custom topic, use that instead
    if custom_topic:
        custom_topic = custom_topic.strip()
        if not custom_topic:
            return jsonify({"error": "Custom topic cannot be empty"}), 400

        # Optionally add custom topic to selected_topics list for visibility
        if game.get("selected_topics") is None:
            game["selected_topics"] = []
        game["selected_topics"].append(custom_topic)

        game["current_topic"] = custom_topic
    else:
        # Validate index selection
        try:
            topic_index = int(topic_index)
        except Exception:
            return jsonify({"error": "Invalid topic index"}), 400

        if topic_index < 0 or topic_index >= len(game["selected_topics"]):
            return jsonify({"error": "Invalid topic index"}), 400

        game["current_topic"] = game["selected_topics"][topic_index]
    game["phase"] = "planning"

    # Reset all players' plans
    for player in game["players"].values():
        player["current_plan"] = None
        player["ready"] = False

    return jsonify({"success": True, "topic": game["current_topic"]})


@app.route("/api/game/<game_id>/submit_plan", methods=["POST"])
def submit_plan(game_id):
    """Submit survival plan"""
    data = request.json
    player_name = data.get("player_name")
    plan = data.get("plan", "").strip()

    if not plan:
        return jsonify({"error": "Plan cannot be empty"}), 400

    game = get_or_create_game(game_id)

    if player_name not in game["players"]:
        return jsonify({"error": "Player not in game"}), 404

    game["players"][player_name]["current_plan"] = plan
    game["players"][player_name]["ready"] = True

    # Check if all players have submitted
    all_ready = all(p["ready"] for p in game["players"].values())

    return jsonify({"success": True, "all_ready": all_ready})


@app.route("/api/game/<game_id>/evaluate", methods=["POST"])
def evaluate_round(game_id):
    """Evaluate all players' survival plans"""
    game = get_or_create_game(game_id)

    if game["phase"] != "planning":
        return jsonify({"error": "Not in planning phase"}), 400

    # Check if all players submitted
    if not all(p["ready"] for p in game["players"].values()):
        return jsonify({"error": "Not all players ready"}), 400

    # Evaluate each player
    round_results = []
    for player_name, player_data in game["players"].items():
        result = judge.judge_survival(
            game["current_topic"], player_name, player_data["current_plan"]
        )

        if result["survived"]:
            player_data["survival_count"] += 1
        else:
            player_data["death_count"] += 1

        round_results.append(
            {
                "player": player_name,
                "survived": result["survived"],
                "reason": result["reason"],
                "plan": player_data["current_plan"],
            }
        )

    game["round_results"].append(
        {
            "round": game["current_round"],
            "topic": game["current_topic"],
            "results": round_results,
        }
    )

    game["phase"] = "results"

    return jsonify({"success": True, "results": round_results})


@app.route("/api/game/<game_id>/next_round", methods=["POST"])
def next_round(game_id):
    """Move to next round or end game"""
    game = get_or_create_game(game_id)

    if game["current_round"] >= game["max_rounds"]:
        game["phase"] = "game_over"

        # Determine winner
        winner = max(game["players"].items(), key=lambda x: x[1]["survival_count"])

        return jsonify(
            {
                "game_over": True,
                "winner": winner[0],
                "final_scores": {
                    name: {
                        "survivals": data["survival_count"],
                        "deaths": data["death_count"],
                    }
                    for name, data in game["players"].items()
                },
            }
        )

    # Next round
    game["current_round"] += 1
    game["phase"] = "topic_selection"

    # Choose new random player for topic selection
    game["topic_chooser"] = random.choice(list(game["players"].keys()))
    game["selected_topics"] = topic_generator.generate_topics()

    return jsonify(
        {
            "game_over": False,
            "next_round": game["current_round"],
            "topic_chooser": game["topic_chooser"],
            "topics": game["selected_topics"],
        }
    )


@app.route("/api/game/<game_id>/state", methods=["GET"])
def get_game_state(game_id):
    """Get current game state"""
    if game_id not in games:
        return jsonify({"error": "Game not found"}), 404

    game = games[game_id]

    return jsonify(
        {
            "phase": game["phase"],
            "current_round": game["current_round"],
            "max_rounds": game["max_rounds"],
            "players": {
                name: {
                    "survival_count": data["survival_count"],
                    "death_count": data["death_count"],
                    "ready": data["ready"],
                }
                for name, data in game["players"].items()
            },
            "topic_chooser": game["topic_chooser"],
            "topics": game["selected_topics"],
            "current_topic": game["current_topic"],
        }
    )


if __name__ == "__main__":
    import os

    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug_mode, host="0.0.0.0", port=5000)
