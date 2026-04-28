"""Example: wrapping an agent loop with Second Brain.

This is framework-agnostic. Replace `generate_response()` with your agent.
"""

from second_brain import Brain


def generate_response(user_message: str) -> str:
    return f"echo: {user_message}"


def run():
    brain = Brain.default()
    brain.init()

    agent_id = "my-agent"

    user_message = "Hello"
    brain.log_event(type="task_started", title=f"Respond to: {user_message}", agent_id=agent_id, tags=["conversation"])

    resp = generate_response(user_message)

    brain.log_event(type="task_completed", title="Responded", details=resp, agent_id=agent_id, tags=["conversation"])
    print(resp)


if __name__ == "__main__":
    run()
