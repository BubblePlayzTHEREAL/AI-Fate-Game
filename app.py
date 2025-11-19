from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
from config import Config
from llama_client import LlamaClient
import secrets

app = Flask(__name__)
app.config.from_object(Config)
socketio = SocketIO(app, cors_allowed_origins="*")

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
            # locks to prevent duplicate actions across clients
            "locks": {
                "start": False,
                "evaluate": False,
                "next_round": False,
            },
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

    # Emit player joined event to all players in the game
    socketio.emit(
        "player_joined",
        {"player_name": player_name, "players": list(game["players"].keys())},
        room=game_id,
    )

    return jsonify({"success": True, "players": list(game["players"].keys())})


@app.route("/api/game/<game_id>/start", methods=["POST"])
def start_game(game_id):
    """Start the game"""
    game = get_or_create_game(game_id)

    # Prevent duplicate start requests
    if game["phase"] != "lobby" or game["locks"].get("start"):
        return jsonify({"error": "Game already started or start locked"}), 400

    if len(game["players"]) < 2:
        return jsonify({"error": "Need at least 2 players"}), 400

    # Lock start action and notify clients so they disable the button
    game["locks"]["start"] = True
    socketio.emit("action_locked", {"action": "start"}, room=game_id)

    game["current_round"] = 1
    game["phase"] = "topic_selection"

    # Choose random player to select topic
    game["topic_chooser"] = random.choice(list(game["players"].keys()))

    # Generate topics
    game["selected_topics"] = topic_generator.generate_topics()

    # Emit game started event to all players
    socketio.emit(
        "game_started",
        {
            "phase": game["phase"],
            "current_round": game["current_round"],
            "topic_chooser": game["topic_chooser"],
            "topics": game["selected_topics"],
        },
        room=game_id,
    )

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

    # Emit topic selected event to all players
    socketio.emit(
        "topic_selected",
        {"phase": game["phase"], "topic": game["current_topic"]},
        room=game_id,
    )

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

    # Emit plan submitted event to all players
    socketio.emit(
        "plan_submitted",
        {
            "player_name": player_name,
            "all_ready": all_ready,
            "players": {
                name: {
                    "survival_count": data["survival_count"],
                    "death_count": data["death_count"],
                    "ready": data["ready"],
                }
                for name, data in game["players"].items()
            },
        },
        room=game_id,
    )

    return jsonify({"success": True, "all_ready": all_ready})


@app.route("/api/game/<game_id>/evaluate", methods=["POST"])
def evaluate_round(game_id):
    """Evaluate all players' survival plans"""
    game = get_or_create_game(game_id)

    if game["phase"] != "planning":
        return jsonify({"error": "Not in planning phase"}), 400

    # Prevent duplicate evaluate requests
    if game["locks"].get("evaluate"):
        return jsonify({"error": "Evaluation already in progress"}), 400

    # Check if all players submitted
    if not all(p["ready"] for p in game["players"].values()):
        return jsonify({"error": "Not all players ready"}), 400

    # Lock evaluation and notify clients so they disable the evaluate button
    game["locks"]["evaluate"] = True
    socketio.emit("action_locked", {"action": "evaluate"}, room=game_id)

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

    # Emit results to ALL players in the game
    socketio.emit(
        "round_results",
        {"phase": game["phase"], "results": round_results},
        room=game_id,
    )

    # unlock evaluate (phase moved to results; keep consistent)
    game["locks"]["evaluate"] = False

    # Notify clients that evaluate action is now unlocked
    socketio.emit("action_unlocked", {"action": "evaluate"}, room=game_id)

    return jsonify({"success": True, "results": round_results})


@app.route("/api/game/<game_id>/next_round", methods=["POST"])
def next_round(game_id):
    """Move to next round or end game"""
    game = get_or_create_game(game_id)

    # Prevent duplicate next_round requests
    if game["locks"].get("next_round"):
        return jsonify({"error": "Next round already in progress"}), 400

    # Lock next_round and notify clients
    game["locks"]["next_round"] = True
    socketio.emit("action_locked", {"action": "next_round"}, room=game_id)

    if game["current_round"] >= game["max_rounds"]:
        game["phase"] = "game_over"

        # Determine winner
        winner = max(game["players"].items(), key=lambda x: x[1]["survival_count"])

        result_data = {
            "game_over": True,
            "phase": game["phase"],
            "winner": winner[0],
            "final_scores": {
                name: {
                    "survivals": data["survival_count"],
                    "deaths": data["death_count"],
                }
                for name, data in game["players"].items()
            },
        }

        # Emit game over event to all players
        socketio.emit("game_over", result_data, room=game_id)

        return jsonify(result_data)

    # Next round
    game["current_round"] += 1
    game["phase"] = "topic_selection"

    # Choose new random player for topic selection
    game["topic_chooser"] = random.choice(list(game["players"].keys()))
    game["selected_topics"] = topic_generator.generate_topics()

    # Reset player plans/ready for the new round
    for p in game["players"].values():
        p["current_plan"] = None
        p["ready"] = False

    # reset locks so actions can be taken in the next round
    game["locks"]["start"] = False
    game["locks"]["evaluate"] = False
    game["locks"]["next_round"] = False

    result_data = {
        "game_over": False,
        "phase": game["phase"],
        "next_round": game["current_round"],
        "topic_chooser": game["topic_chooser"],
        "topics": game["selected_topics"],
        "players": {
            name: {
                "survival_count": data["survival_count"],
                "death_count": data["death_count"],
                "ready": data.get("ready", False),
            }
            for name, data in game["players"].items()
        },
    }

    # Emit next round event to all players
    socketio.emit("next_round", result_data, room=game_id)

    return jsonify(result_data)


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


@socketio.on("connect")
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")


@socketio.on("join_game_room")
def handle_join_game_room(data):
    """Join a game room for WebSocket updates"""
    game_id = data.get("game_id")
    player_name = data.get("player_name")

    if game_id:
        join_room(game_id)
        print(f"Player {player_name} joined room {game_id}")
        emit("joined_room", {"game_id": game_id, "player_name": player_name})


@socketio.on("leave_game_room")
def handle_leave_game_room(data):
    """Leave a game room"""
    game_id = data.get("game_id")
    player_name = data.get("player_name")

    if game_id:
        leave_room(game_id)
        print(f"Player {player_name} left room {game_id}")


if __name__ == "__main__":
    import os

    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    socketio.run(app, debug=debug_mode, host="0.0.0.0", port=5000)
