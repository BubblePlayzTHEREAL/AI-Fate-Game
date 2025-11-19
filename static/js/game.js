const gameId = document.getElementById('gameId').textContent;
const playerName = document.getElementById('playerName').textContent;
let currentPhase = 'lobby';
let gameState = {};

// Initialize Socket.IO connection
const socket = io();

// Socket.IO event handlers
socket.on('connect', () => {
    console.log('WebSocket connected');
    // Join the game room
    socket.emit('join_game_room', { game_id: gameId, player_name: playerName });
});

socket.on('disconnect', () => {
    console.log('WebSocket disconnected');
});

socket.on('joined_room', (data) => {
    console.log('Joined game room:', data);
});

socket.on('player_joined', (data) => {
    console.log('Player joined:', data);
    // Refresh game state when a player joins
    fetchGameState();
});

socket.on('game_started', (data) => {
    console.log('Game started:', data);
    gameState.phase = data.phase;
    gameState.current_round = data.current_round;
    gameState.topic_chooser = data.topic_chooser;
    gameState.topics = data.topics;
    updateUI(gameState);
});

socket.on('topic_selected', (data) => {
    console.log('Topic selected:', data);
    gameState.phase = data.phase;
    gameState.current_topic = data.topic;
    updateUI(gameState);
});

socket.on('plan_submitted', (data) => {
    console.log('Plan submitted:', data);
    gameState.players = data.players;
    updateUI(gameState);
});

socket.on('round_results', (data) => {
    console.log('Round results:', data);
    gameState.phase = data.phase;
    displayResults(data.results);
    showPhase('results');
});

socket.on('next_round', (data) => {
    console.log('Next round:', data);
    gameState.phase = data.phase;
    gameState.current_round = data.next_round;
    gameState.topic_chooser = data.topic_chooser;
    gameState.topics = data.topics;
    
    // Reset planning phase UI
    document.getElementById('survivalPlan').value = '';
    document.getElementById('survivalPlan').disabled = false;
    document.getElementById('submitPlanBtn').style.display = 'block';
    document.getElementById('waitingForPlayers').style.display = 'none';
    document.getElementById('evaluateBtn').style.display = 'none';
    
    updateUI(gameState);
});

socket.on('game_over', (data) => {
    console.log('Game over:', data);
    gameState.phase = data.phase;
    displayGameOver(data);
    showPhase('game_over');
});

// Join game on load
async function joinGame() {
    try {
        const response = await fetch(`/api/game/${gameId}/join`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_name: playerName })
        });

        if (response.ok) {
            console.log('Joined game successfully');
            // Fetch initial game state
            fetchGameState();
        } else {
            alert('Failed to join game');
        }
    } catch (error) {
        console.error('Error joining game:', error);
    }
}

// Fetch game state (used for initial load and when needed)
async function fetchGameState() {
    try {
        const response = await fetch(`/api/game/${gameId}/state`);
        const data = await response.json();

        gameState = data;
        updateUI(data);
    } catch (error) {
        console.error('Error fetching game state:', error);
    }
}

// Update UI based on game state
function updateUI(state) {
    // Update round info
    document.getElementById('currentRound').textContent = state.current_round;
    document.getElementById('maxRounds').textContent = state.max_rounds;

    // Update players list
    updatePlayersList(state.players);

    // Show appropriate phase
    if (state.phase !== currentPhase) {
        currentPhase = state.phase;
        showPhase(state.phase);
    }

    // Update phase-specific content
    switch (state.phase) {
        case 'lobby':
            updateLobbyPhase(state);
            break;
        case 'topic_selection':
            updateTopicSelectionPhase(state);
            break;
        case 'planning':
            updatePlanningPhase(state);
            break;
        case 'results':
            // Results are static once loaded
            break;
        case 'game_over':
            // Game over is static once loaded
            break;
    }
}

function updatePlayersList(players) {
    const playersList = document.getElementById('playersList');
    playersList.innerHTML = '';

    for (const [name, data] of Object.entries(players)) {
        const card = document.createElement('div');
        card.className = 'player-card' + (data.ready ? ' ready' : '');
        card.innerHTML = `
            <div class="player-name">${name}</div>
            <div class="player-stats">
                ✓ ${data.survival_count} | ✗ ${data.death_count}
            </div>
        `;
        playersList.appendChild(card);
    }
}

function showPhase(phase) {
    // Hide all phases
    document.querySelectorAll('.phase-container').forEach(el => {
        el.style.display = 'none';
    });

    // Show current phase
    const phaseMap = {
        'lobby': 'lobbyPhase',
        'topic_selection': 'topicSelectionPhase',
        'planning': 'planningPhase',
        'results': 'resultsPhase',
        'game_over': 'gameOverPhase'
    };

    const phaseId = phaseMap[phase];
    if (phaseId) {
        document.getElementById(phaseId).style.display = 'block';
    }
}

function updateLobbyPhase(state) {
    const playerCount = Object.keys(state.players).length;
    const canStart = playerCount >= 2;

    document.getElementById('startGameBtn').disabled = !canStart;
}

function updateTopicSelectionPhase(state) {
    const isChooser = state.topic_chooser === playerName;
    const chooserText = isChooser
        ? "You choose the topic!"
        : `${state.topic_chooser} is choosing the topic...`;

    document.getElementById('topicChooserText').textContent = chooserText;

    const topicsList = document.getElementById('topicsList');
    topicsList.innerHTML = '';

    if (state.topics) {
        state.topics.forEach((topic, index) => {
            const card = document.createElement('div');
            card.className = 'topic-card';
            if (isChooser) {
                card.onclick = () => selectTopic(index);
            } else {
                card.style.cursor = 'default';
            }
            card.innerHTML = `
                <div class="topic-number">Option ${index + 1}</div>
                <div>${topic}</div>
            `;
            topicsList.appendChild(card);
        });
        // If chooser, allow creating a custom topic
        if (isChooser) {
            const customCard = document.createElement('div');
            customCard.className = 'topic-card custom-topic';
            customCard.onclick = () => selectCustomTopic();
            customCard.innerHTML = `
                <div class="topic-number">Custom</div>
                <div>Create your own scenario...</div>
            `;
            topicsList.appendChild(customCard);
        }
    }
}

function updatePlanningPhase(state) {
    document.getElementById('currentTopic').textContent = state.current_topic;

    const myPlayer = state.players[playerName];
    if (myPlayer && myPlayer.ready) {
        document.getElementById('survivalPlan').disabled = true;
        document.getElementById('submitPlanBtn').style.display = 'none';
        document.getElementById('waitingForPlayers').style.display = 'block';

        // Update ready players list
        const readyPlayers = document.getElementById('readyPlayers');
        const readyList = Object.entries(state.players)
            .filter(([_, data]) => data.ready)
            .map(([name, _]) => name);
        readyPlayers.innerHTML = `Ready: ${readyList.join(', ')}`;

        // Check if all players ready
        const allReady = Object.values(state.players).every(p => p.ready);
        if (allReady) {
            document.getElementById('evaluateBtn').style.display = 'block';
        }
    }
}

// Event Handlers
document.getElementById('copyGameIdBtn').addEventListener('click', () => {
    navigator.clipboard.writeText(gameId);
    alert('Game ID copied to clipboard!');
});

document.getElementById('startGameBtn').addEventListener('click', async () => {
    try {
        const response = await fetch(`/api/game/${gameId}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            const error = await response.json();
            alert(error.error || 'Failed to start game');
        }
    } catch (error) {
        console.error('Error starting game:', error);
    }
});

async function selectTopic(index) {
    try {
        const response = await fetch(`/api/game/${gameId}/select_topic`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                player_name: playerName,
                topic_index: index
            })
        });

        if (!response.ok) {
            const error = await response.json();
            alert(error.error || 'Failed to select topic');
        }
    } catch (error) {
        console.error('Error selecting topic:', error);
    }
}

async function selectCustomTopic() {
    const custom = prompt('Enter your custom survival scenario:');
    if (!custom) return;

    try {
        const response = await fetch(`/api/game/${gameId}/select_topic`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                player_name: playerName,
                custom_topic: custom
            })
        });

        if (!response.ok) {
            const error = await response.json();
            alert(error.error || 'Failed to select custom topic');
        }
    } catch (error) {
        console.error('Error selecting custom topic:', error);
    }
}

document.getElementById('submitPlanBtn').addEventListener('click', async () => {
    const plan = document.getElementById('survivalPlan').value.trim();

    if (!plan) {
        alert('Please write a survival plan!');
        return;
    }

    try {
        const response = await fetch(`/api/game/${gameId}/submit_plan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                player_name: playerName,
                plan: plan
            })
        });

        if (!response.ok) {
            const error = await response.json();
            alert(error.error || 'Failed to submit plan');
        }
    } catch (error) {
        console.error('Error submitting plan:', error);
    }
});

document.getElementById('evaluateBtn').addEventListener('click', async () => {
    document.getElementById('evaluateBtn').disabled = true;
    document.getElementById('evaluateBtn').textContent = 'Evaluating...';

    try {
        const response = await fetch(`/api/game/${gameId}/evaluate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            const data = await response.json();
            displayResults(data.results);
        } else {
            const error = await response.json();
            alert(error.error || 'Failed to evaluate');
            document.getElementById('evaluateBtn').disabled = false;
            document.getElementById('evaluateBtn').textContent = 'Evaluate All Plans';
        }
    } catch (error) {
        console.error('Error evaluating:', error);
        document.getElementById('evaluateBtn').disabled = false;
        document.getElementById('evaluateBtn').textContent = 'Evaluate All Plans';
    }
});

function displayResults(results) {
    const container = document.getElementById('resultsContainer');
    container.innerHTML = '';

    results.forEach(result => {
        const card = document.createElement('div');
        card.className = `result-card ${result.survived ? 'survived' : 'died'}`;
        card.innerHTML = `
            <div class="result-header">
                <strong>${result.player}</strong>
                <span class="result-status ${result.survived ? 'survived' : 'died'}">
                    ${result.survived ? '✓ SURVIVED' : '✗ DIED'}
                </span>
            </div>
            <div class="result-reason">${result.reason}</div>
            <div class="result-plan">
                <strong>Plan:</strong> ${result.plan}
            </div>
        `;
        container.appendChild(card);
    });
}

document.getElementById('nextRoundBtn').addEventListener('click', async () => {
    document.getElementById('nextRoundBtn').disabled = true;
    document.getElementById('nextRoundBtn').textContent = 'Loading...';

    try {
        const response = await fetch(`/api/game/${gameId}/next_round`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            const data = await response.json();

            if (data.game_over) {
                displayGameOver(data);
            } else {
                // Reset planning phase
                document.getElementById('survivalPlan').value = '';
                document.getElementById('survivalPlan').disabled = false;
                document.getElementById('submitPlanBtn').style.display = 'block';
                document.getElementById('waitingForPlayers').style.display = 'none';
                document.getElementById('evaluateBtn').style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error moving to next round:', error);
    } finally {
        document.getElementById('nextRoundBtn').disabled = false;
        document.getElementById('nextRoundBtn').textContent = 'Next Round';
    }
});

function displayGameOver(data) {
    const winnerDisplay = document.getElementById('winnerDisplay');
    winnerDisplay.innerHTML = `
        <h3>🏆 Winner: ${data.winner}! 🏆</h3>
        <p>Congratulations on your survival skills!</p>
    `;

    const finalScores = document.getElementById('finalScores');
    finalScores.innerHTML = '';

    for (const [name, scores] of Object.entries(data.final_scores)) {
        const card = document.createElement('div');
        card.className = 'final-score-card';
        card.innerHTML = `
            <div class="player-name">${name}</div>
            <div class="final-stats">
                <div class="stat">
                    <div class="stat-value survived-stat">${scores.survivals}</div>
                    <div class="stat-label">Survived</div>
                </div>
                <div class="stat">
                    <div class="stat-value died-stat">${scores.deaths}</div>
                    <div class="stat-label">Died</div>
                </div>
            </div>
        `;
        finalScores.appendChild(card);
    }
}

// Initialize
joinGame();
