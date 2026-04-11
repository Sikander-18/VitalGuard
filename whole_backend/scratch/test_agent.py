import asyncio
import json
from backend.agents.graph import agent_graph

async def test():
    state = {
        "vitals": {"bpm": 180, "spo2": 85, "systolic": 200, "diastolic": 120, "hrv": 10},
        "user_id": "test_user",
        "condition": None,
        "severity": None,
        "reasoning": None
    }
    print("Invoking agent...")
    try:
        final_state = agent_graph.invoke(state)
        print("Final State:", json.dumps(final_state, indent=2))
    except Exception as e:
        print("Agent error:", str(e))

if __name__ == "__main__":
    asyncio.run(test())
