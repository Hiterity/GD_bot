import os
from datetime import datetime, timezone

from mistralai.client import Mistral


DEFAULT_AI_MODEL = "mistral-large-latest"
MAX_AGENT_HISTORY_MESSAGES = 20
MAX_AGENT_OUTPUT_TOKENS = 900
MAX_PUBLIC_SOURCES = 5
PLACEHOLDER_API_KEYS = {
    "your_mistral_api_key",
    "your-api-key",
    "replace_with_your_real_mistral_api_key",
    "replace_me"
}

AI_CONFIGURATION_MESSAGE = (
    "AI chat is not configured yet. Replace `MISTRAL_API_KEY` in your `.env` "
    "file with a real Mistral AI API key, then restart the bot."
)


SYSTEM_PROMPT = """
You are DashGuide, the GD Demon List AI Agent inside a Telegram bot.

Personality and tone:
- Sound like a knowledgeable Geometry Dash friend: relaxed, direct, and a bit
  enthusiastic, but never fake-hype or spammy.
- Talk naturally in short paragraphs. Avoid robotic phrases like "based on the
  provided context" unless the distinction really matters.
- Give clear opinions when useful, but label them as opinion.
- If a user is casual, answer casually. If they ask for details, get specific.

Core job:
- Talk with users about Geometry Dash, Pointercrate Demonlist updates, extreme
  demons, player profiles, daily challenges, records, progression, gameplay,
  creators, verifiers, and general game topics.
- Use saved chat history to preserve continuity, preferences, and follow-up
  context. Do not make the user repeat themselves.
- Use the live bot context for current Pointercrate rankings, stored daily
  challenges, and recently detected Demonlist changes.
- Use web search for questions that may require recent public information,
  public sources, current events, new Geometry Dash updates, recent records,
  player news, creator/verifier updates, or details missing from local context.

Source behavior:
- Prefer reputable public sources: Pointercrate, GDBrowser, official
  Geometry Dash/RobTop channels, Steam pages, official social posts, and
  well-known community resources.
- Use sources to verify current claims. Do not invent URLs or pretend you
  searched if you did not.
- When public web information affects the answer, include concise source links.
- If sources disagree or look stale, say that briefly and give the safest read.

Answer quality:
- Lead with the answer, then add context.
- For "who is top / what is #1 / latest list" questions, use the live Top 10
  context first, then web search if the user asks for newest public discussion
  or details beyond the ranking.
- For broad game questions, explain like a good coach: practical, concrete, and
  easy to act on.
- Ask one short follow-up only when it would materially improve the answer.
- Do not claim that a user completed a challenge, has points, or is subscribed
  unless the bot context explicitly says so.
""".strip()


def get_ai_model() -> str:
    return os.environ.get("MISTRAL_MODEL", DEFAULT_AI_MODEL)


def get_mistral_api_key():
    api_key = os.environ.get("MISTRAL_API_KEY", "").strip()

    if not api_key or api_key in PLACEHOLDER_API_KEYS:
        return None

    return api_key


def is_ai_configured() -> bool:
    return get_mistral_api_key() is not None


def format_chat_history(chat_history: list[dict]) -> str:
    if not chat_history:
        return "No previous AI conversation history for this user."

    lines = []

    for message in chat_history[-MAX_AGENT_HISTORY_MESSAGES:]:
        role = message.get("role", "user").title()
        content = message.get("content", "")
        lines.append(f"{role}: {content}")

    return "\n".join(lines)


def build_conversation_input(
    user_message: str,
    chat_history: list[dict],
    live_context: str
) -> str:
    return (
        f"Current date: {datetime.now(timezone.utc).date().isoformat()} UTC\n\n"
        "Use the local bot context, saved user conversation history, and public "
        "web search when useful. Answer the newest user message naturally, as a "
        "continuation of the conversation.\n\n"
        f"Local bot context:\n{live_context}\n\n"
        f"Saved AI chat history:\n{format_chat_history(chat_history)}\n\n"
        f"Newest user message:\n{user_message}"
    )


def chunk_to_text(chunk) -> str:
    if isinstance(chunk, str):
        return chunk

    if isinstance(chunk, dict):
        if chunk.get("type") == "text":
            return chunk.get("text", "")

        if chunk.get("type") == "tool_reference":
            return ""

        return chunk.get("text") or chunk.get("content") or ""

    chunk_type = getattr(chunk, "type", None)

    if chunk_type == "text":
        return getattr(chunk, "text", "") or ""

    if chunk_type == "tool_reference":
        return ""

    return getattr(chunk, "text", "") or getattr(chunk, "content", "") or ""


def source_from_chunk(chunk):
    if isinstance(chunk, dict):
        if chunk.get("type") != "tool_reference":
            return None

        title = chunk.get("title") or chunk.get("source") or "Source"
        url = chunk.get("url")
    else:
        if getattr(chunk, "type", None) != "tool_reference":
            return None

        title = (
            getattr(chunk, "title", None)
            or getattr(chunk, "source", None)
            or "Source"
        )
        url = getattr(chunk, "url", None)

    if not url:
        return None

    return title, url


def extract_conversation_text(response) -> str:
    text_parts = []
    sources = []
    seen_urls = set()

    for output in getattr(response, "outputs", []):
        if getattr(output, "type", None) != "message.output":
            continue

        content = getattr(output, "content", "")

        if isinstance(content, str):
            text_parts.append(content)
            continue

        for chunk in content:
            text = chunk_to_text(chunk)

            if text:
                text_parts.append(text)

            source = source_from_chunk(chunk)

            if source is None:
                continue

            title, url = source

            if url in seen_urls:
                continue

            seen_urls.add(url)
            sources.append((title, url))

    answer = "\n".join(part.strip() for part in text_parts if part.strip())

    if sources:
        source_lines = [
            f"- [{title}]({url})"
            for title, url in sources[:MAX_PUBLIC_SOURCES]
        ]
        answer = f"{answer}\n\nSources:\n" + "\n".join(source_lines)

    return answer.strip()


async def generate_agent_reply(
    user_message: str,
    chat_history: list[dict],
    live_context: str
) -> str:
    api_key = get_mistral_api_key()

    if api_key is None:
        return AI_CONFIGURATION_MESSAGE

    async with Mistral(api_key=api_key) as client:
        response = await client.beta.conversations.start_async(
            model=get_ai_model(),
            instructions=SYSTEM_PROMPT,
            inputs=build_conversation_input(
                user_message=user_message,
                chat_history=chat_history,
                live_context=live_context
            ),
            tools=[
                {
                    "type": "web_search"
                }
            ],
            completion_args={
                "max_tokens": MAX_AGENT_OUTPUT_TOKENS
            },
            store=False
        )

    content = extract_conversation_text(response)

    if not content:
        return "I could not generate a response this time. Try again in a moment."

    return content.strip()
