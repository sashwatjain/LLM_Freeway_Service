import asyncio
import time
from datetime import datetime
from pathlib import Path

from app.config import settings
from app.providers.registry import registry
from app.providers.openrouter import OpenRouterProvider
from app.providers.groq import GroqProvider
from app.providers.gemini import GeminiProvider
from app.providers.cohere import CohereProvider
from app.providers.cloudflare import CloudflareProvider
from app.providers.hyperbolic import HyperbolicProvider
from app.providers.sambanova import SambaNovaProvider
from app.providers.scaleway import ScalewayProvider
from app.providers.mistral import MistralProvider
from app.providers.cerebras import CerebrasProvider
from app.providers.kluster import KlusterProvider
from app.providers.github import GitHubProvider
from app.providers.nvidia import NVIDIAProvider


def _init():
    registry.register(OpenRouterProvider())
    registry.register(GroqProvider())
    registry.register(GeminiProvider())
    registry.register(CohereProvider())
    registry.register(CloudflareProvider())
    registry.register(HyperbolicProvider())
    registry.register(SambaNovaProvider())
    registry.register(ScalewayProvider())
    registry.register(MistralProvider())
    registry.register(CerebrasProvider())
    registry.register(KlusterProvider())
    registry.register(GitHubProvider())
    registry.register(NVIDIAProvider())


def _check_key(provider_name: str) -> str:
    key_map = {
        "openrouter": settings.openrouter_api_key,
        "groq": settings.groq_api_key,
        "gemini": settings.google_api_key,
        "cohere": settings.cohere_api_key,
        "cloudflare": settings.cloudflare_api_key,
        "hyperbolic": settings.hyperbolic_api_key,
        "sambanova": settings.samba_api_key,
        "scaleway": settings.scaleway_api_key,
        "mistral": settings.mistral_api_key,
        "cerebras": settings.cerebras_api_key,
        "kluster": settings.kluster_api_key,
        "github": settings.github_token,
        "nvidia": settings.nvidia_api_key,
    }
    return "KEY OK" if key_map.get(provider_name) else "MISSING"


def _limits_str(limits) -> str:
    if not limits:
        return "none"
    d = limits.model_dump(exclude_none=True)
    if not d:
        return "none"
    return ", ".join(f"{k}={v}" for k, v in d.items())


async def test_provider(provider_name: str, provider) -> dict:
    result = {
        "name": provider_name,
        "configured": provider.configured,
        "key_present": _check_key(provider_name),
        "models_count": 0,
        "models": [],
        "chat_test": None,
        "chat_model": None,
        "error": None,
        "elapsed": 0,
    }

    t0 = time.time()
    try:
        models = await provider.list_models()
        result["models"] = [
            {
                "id": m.id,
                "name": m.name,
                "limits": _limits_str(m.limits),
            }
            for m in models
        ]
        result["models_count"] = len(models)
    except Exception as e:
        result["error"] = f"list_models: {e}"
        result["elapsed"] = time.time() - t0
        return result

    if provider.configured and models:
        try:
            from app.schemas import Message
            test_model = models[0]["id"] if isinstance(models[0], dict) else models[0].id
            result["chat_model"] = test_model
            resp = await provider.chat(
                messages=[Message(role="user", content="Reply with just the word OK")],
                model=test_model,
                system_prompt="You are a test assistant. Keep responses extremely short.",
            )
            text = ""
            for c in resp.choices:
                text += c.get("message", {}).get("content", "")
            result["chat_test"] = text.strip()[:100] or "empty response"
        except Exception as e:
            result["chat_test"] = f"FAILED: {e}"

    result["elapsed"] = time.time() - t0
    return result


def _write_report(all_results: list[dict]):
    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = Path(__file__).parent / f"provider_report_{now}.txt"

    lines = []
    sep = "=" * 100
    short_sep = "-" * 100

    lines.append(sep)
    lines.append(f"  LLM-Freeway Provider Test Report")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Providers: {len(all_results)}")
    lines.append(sep)
    lines.append("")

    total_configured = sum(1 for r in all_results if r["configured"])
    total_models = sum(r["models_count"] for r in all_results)
    lines.append(f"Configured providers: {total_configured}/{len(all_results)}")
    lines.append(f"Total models across all providers: {total_models}")
    lines.append("")

    lines.append(short_sep)
    header = f"{'Provider':<18} {'Key':<12} {'Models':<7} {'Time':<7} {'Chat Status':<60}"
    lines.append(header)
    lines.append(short_sep)

    for r in all_results:
        key_status = r["key_present"]
        chat_status = "OK" if r["chat_test"] and not str(r["chat_test"]).startswith("FAILED") else (r["chat_test"] or "SKIPPED")
        if chat_status and len(str(chat_status)) > 55:
            chat_status = str(chat_status)[:52] + "..."
        elapsed_s = f"{r['elapsed']:.1f}s"
        lines.append(f"{r['name']:<18} {key_status:<12} {r['models_count']:<7} {elapsed_s:<7} {str(chat_status):<60}")

    lines.append(short_sep)

    for r in all_results:
        if r["error"]:
            lines.append(f"\n  !!! {r['name']}: {r['error']}")

    lines.append("")
    lines.append(sep)
    lines.append("  MODEL DETAILS")
    lines.append(sep)

    for r in all_results:
        lines.append("")
        lines.append(f"  [{r['name'].upper()}]  ({r['models_count']} models, key: {r['key_present']})")
        if r["chat_model"] and r["chat_test"] and not str(r["chat_test"]).startswith("FAILED"):
            lines.append(f"  Chat test: OK on '{r['chat_model']}'")
        elif r["chat_test"] and str(r["chat_test"]).startswith("FAILED"):
            lines.append(f"  Chat test: {r['chat_test']}")
        else:
            lines.append(f"  Chat test: SKIPPED")
        lines.append("")

        if r["models"]:
            lines.append(f"  {'Model ID':<55} {'Name':<35} {'Limits'}")
            lines.append(f"  {'-'*55:<55} {'-'*35:<35} {'-'*40}")
            for m in r["models"]:
                lines.append(f"  {m['id']:<55} {m['name']:<35} {m['limits']}")
        else:
            lines.append("  (no models)")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


async def main():
    print("Testing all providers...\n")

    _init()
    providers = registry.list_all()

    all_results = []
    for p in providers:
        print(f"  {p.name}... ", end="", flush=True)
        result = await test_provider(p.name, p)
        status = "OK" if result["error"] is None else "FAIL"
        print(f"{status} ({result['elapsed']:.1f}s)")
        all_results.append(result)

    report_path = _write_report(all_results)
    print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
