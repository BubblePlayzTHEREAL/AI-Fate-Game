import requests
import json


class LlamaClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def generate(self, prompt, model="dolphin3"):
        """Generate text using Llama model"""
        try:
            url = f"{self.base_url}/api/generate"
            payload = {"model": model, "prompt": prompt, "stream": False}
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            print(f"Error calling Llama model: {e}")
            return None

    def generate_topics(self):
        """Generate 3 deathly scenario topics"""
        prompt = """Generate exactly 3 dangerous survival scenarios. Each should be a single sentence describing a life-threatening situation.
Format your response as a numbered list:
1. [First scenario]
2. [Second scenario]
3. [Third scenario]

Examples of scenarios:
- You are trapped in a burning building on the 10th floor
- A massive tsunami is heading toward your coastal town
- You are lost in the Arctic with no supplies

Generate 3 NEW creative and dangerous scenarios now:"""

        response = self.generate(prompt)
        if response:
            # Parse the response to extract topics
            topics = []
            lines = response.strip().split("\n")
            for line in lines:
                line = line.strip()
                # Look for numbered lines (1., 2., 3.)
                if line and (line[0].isdigit() or line.startswith("-")):
                    # Remove numbering and clean up
                    topic = line.lstrip("0123456789.-) ").strip()
                    if topic:
                        topics.append(topic)

            # If parsing failed, return fallback topics
            if len(topics) < 3:
                topics = [
                    "You are stranded on a deserted island with limited supplies and dangerous wildlife",
                    "A deadly pandemic has broken out and society is collapsing around you",
                    "You wake up in an underground bunker with no memory and the air supply is running out",
                ]

            return topics[:3]
        else:
            # Fallback topics if API fails
            return [
                "You are trapped in a zombie apocalypse in a shopping mall",
                "A massive earthquake has destroyed your city and you are buried under rubble",
                "You are lost in a dense jungle with predators hunting you",
            ]

    def judge_survival(self, topic, player_name, survival_plan):
        """Evaluate if a player survives based on their plan"""
        prompt = f"""You are a survival judge. A player named {player_name} is facing this situation:
{topic}

Their survival plan is:
{survival_plan}

Evaluate their plan and determine if they would survive or die. Consider:
- Realism of the plan
- Resourcefulness
- Logical thinking
- Completeness of the solution

Respond with EXACTLY ONE of these two formats:
SURVIVED: [brief reason why they survived]
DIED: [brief reason why they died]

Your judgment:"""

        response = self.generate(prompt)
        if response:
            response_upper = response.upper()
            if "SURVIVED" in response_upper:
                # Extract reason after SURVIVED:
                parts = response.split(":", 1)
                reason = (
                    parts[1].strip() if len(parts) > 1 else "Their plan was adequate"
                )
                return {"survived": True, "reason": reason}
            elif "DIED" in response_upper:
                # Extract reason after DIED:
                parts = response.split(":", 1)
                reason = (
                    parts[1].strip() if len(parts) > 1 else "Their plan was inadequate"
                )
                return {"survived": False, "reason": reason}

        # Default to random-ish outcome based on plan length as fallback
        survived = len(survival_plan) > 50
        return {
            "survived": survived,
            "reason": "Detailed planning saved them"
            if survived
            else "Plan lacked detail",
        }
