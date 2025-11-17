# Gameplay Guide

## Starting a Game

### Option 1: Create New Game
1. Visit the home page at `http://localhost:5000`
2. Click "Create Game" button
3. Enter your player name when prompted
4. Share the Game ID with friends to join

### Option 2: Join Existing Game
1. Get the Game ID from the game creator
2. Enter the Game ID in the "Join Existing Game" section
3. Enter your player name
4. Click "Join Game"

## Game Phases

### 1. Lobby Phase
- **Wait for Players**: At least 2 players needed to start
- **Player List**: Shows all joined players with their scores (✓ = Survivals, ✗ = Deaths)
- **Start Game**: First player (or any player) clicks "Start Game" when ready

### 2. Topic Selection Phase
- **Random Chooser**: The game randomly selects one player to pick the scenario
- **3 Options**: The AI generates 3 deadly scenarios to choose from
  - Example: "You are trapped in a burning building on the 10th floor"
  - Example: "A massive tsunami is heading toward your coastal town"
  - Example: "You are lost in the Arctic with no supplies"
- **Selection**: The chosen player clicks on their preferred scenario

### 3. Planning Phase
- **Scenario Display**: The chosen scenario is shown to all players
- **Write Plan**: Each player writes their survival strategy in the text area
- **Submit**: Click "Submit Plan" when your plan is ready
- **Waiting**: Once submitted, wait for all other players to finish
- **Evaluate**: When everyone is ready, click "Evaluate All Plans"

### 4. Results Phase
- **Outcomes**: Each player's result is displayed:
  - ✓ **SURVIVED**: Green card with survival reason
  - ✗ **DIED**: Red card with death reason
- **AI Reasoning**: The judge explains why each player survived or died
- **Plans Visible**: All players can see each other's survival plans
- **Next Round**: Click "Next Round" to continue

### 5. Game Over Phase
- **Winner Announced**: 🏆 The player with most survivals wins
- **Final Scores**: Shows survival/death counts for all players
- **Play Again**: Return to home page to start a new game

## Tips for Survival

1. **Be Specific**: Detailed plans perform better than vague ones
2. **Think Realistically**: The AI judges based on realistic survival tactics
3. **Consider Resources**: Mention what resources you'd use and how
4. **Step-by-Step**: Break down your plan into clear steps
5. **Address Dangers**: Acknowledge the main threats and how you'd handle them

## Example Good Survival Plan

**Scenario**: "You are trapped in a burning building on the 10th floor"

**Good Plan**:
```
First, I would feel doors before opening to check for heat. I'd stay low 
to avoid smoke inhalation and wet a cloth to cover my mouth. I would 
find the nearest stairwell (avoiding elevators) and descend while keeping 
one hand on the wall. If the stairwell is blocked by fire, I'd retreat to 
a room with a window, seal the door with wet towels, and signal for help 
from the window while waiting for rescue.
```

**Why it works**: Specific actions, realistic tactics, considers multiple scenarios, shows knowledge of fire safety.

## Scoring

- Each round, players either **Survive** (+1 to survival count) or **Die** (+1 to death count)
- After all rounds (default: 5), the player with the **most survivals wins**
- Ties go to the player with fewer deaths

## Real-time Updates

- The game state refreshes every 2 seconds
- No need to manually refresh the page
- Player readiness indicators update automatically
- Round progress tracked in real-time

## Troubleshooting

**"Need at least 2 players"**
- Wait for another player to join before starting

**"Not your turn to choose"**
- Only the randomly selected player can pick the topic

**"Plan cannot be empty"**
- You must write something in your survival plan

**Topics are generic/boring**
- Check that your Llama model is running and accessible
- Try using a different or newer Llama model

## Advanced Features

### Multiple Games
- You can run multiple games simultaneously
- Each game has a unique Game ID
- Games are independent of each other

### Configurable Rounds
- Set `MAX_ROUNDS` in `.env` to change game length
- Default is 5 rounds

### Different AI Models
- Point `LLAMA_TOPIC_IP` and `LLAMA_JUDGE_IP` to different models
- Use more creative models for topics
- Use stricter models for judging
