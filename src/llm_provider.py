import ollama

from config import get_ollama_base_url, get_ollama_model

_selected_model: str | None = None


def _client() -> ollama.Client:
    return ollama.Client(host=get_ollama_base_url())


def list_models() -> list[str]:
    response = _client().list()
    return sorted(model.model for model in response.models)


def select_model(model: str) -> None:
    global _selected_model
    _selected_model = model


def get_active_model() -> str | None:
    return _selected_model or get_ollama_model() or None


def is_ollama_available() -> bool:
    try:
        list_models()
        return True
    except Exception:
        return False


def generate_text(prompt: str, model_name: str | None = None) -> str:
    model = model_name or get_active_model()
    if not model:
        raise RuntimeError(
            "No Ollama model configured. Set ollama_model in config.json first."
        )

    response = _client().chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"].strip()
