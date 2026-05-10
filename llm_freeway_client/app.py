import streamlit as st
from utils.api_client import FreewayClient, FreewayClientError

st.set_page_config(page_title="LLM-Freeway", page_icon="", layout="centered")

if "client" not in st.session_state:
    st.session_state.client = FreewayClient()
if "providers" not in st.session_state:
    st.session_state.providers = []
if "models" not in st.session_state:
    st.session_state.models = []
if "prev_provider" not in st.session_state:
    st.session_state.prev_provider = ""
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "continue_messages" not in st.session_state:
    st.session_state.continue_messages = []

client: FreewayClient = st.session_state.client

# ── Fetch providers once per session (lazy) ──
if not st.session_state.providers:
    try:
        st.session_state.providers = client.list_providers()
    except Exception:
        pass

providers = st.session_state.providers
configured_names = [p["name"] for p in providers if p["configured"]]
all_names = [p["name"] for p in providers]

# ── Sidebar ──
st.sidebar.title("LLM-Freeway")
try:
    h = client.health()
    st.sidebar.caption(f"`{client.base_url}`  \n{h.get('configured', '?')}/{h.get('providers', '?')} ready")
except Exception:
    st.sidebar.error("Service unreachable")

mode = st.sidebar.radio("Mode", ["Chat", "ContinueChat"], label_visibility="collapsed")
st.sidebar.divider()

opts = configured_names if configured_names else all_names
default_opt = opts[0] if opts else "github"

# ── Chat controls ──
if mode == "Chat":
    chat_provider = st.sidebar.selectbox("Provider", opts, key="cp")

    # Only fetch models when provider changes
    if chat_provider != st.session_state.prev_provider:
        try:
            st.session_state.models = client.list_models(chat_provider)
        except Exception:
            st.session_state.models = []
        st.session_state.prev_provider = chat_provider

    models = st.session_state.models
    if models:
        chat_model = st.sidebar.selectbox(
            "Model", models,
            format_func=lambda m: f"{m.get('name', m['id'])} ({m['id']})" if isinstance(m, dict) else m,
            key="cm",
        )
        chat_model_id = chat_model["id"] if isinstance(chat_model, dict) else chat_model
    else:
        chat_model_id = st.sidebar.text_input("Model ID", value="Ministral-3B", key="cmi")

    chat_system = st.sidebar.text_area("System prompt", value="You are a helpful assistant.", key="cs")
    chat_memory = st.sidebar.checkbox("Memory", key="cme")
    chat_session = st.sidebar.text_input("Session ID", placeholder="optional", key="csi")

# ── ContinueChat controls ──
if mode == "ContinueChat":
    cont_priority = st.sidebar.multiselect(
        "Provider priority", opts,
        default=opts[:3] if len(opts) >= 3 else opts,
        key="cop",
    )
    cont_system = st.sidebar.text_area("System prompt", value="You are a helpful assistant.", key="cos")
    cont_memory = st.sidebar.checkbox("Memory", key="come")
    cont_session = st.sidebar.text_input("Session ID", placeholder="optional", key="cossi")

# ── Minimal sidebar extras ──
with st.sidebar.expander("Providers", expanded=False):
    for p in providers:
        icon = "✅" if p["configured"] else "❌"
        st.markdown(f"{icon} **{p['name']}**  \n{p.get('models_count', '?')} models")

with st.sidebar.expander("Memory", expanded=False):
    mem_id = st.text_input("Session to clear", key="mem_inp", placeholder="session-123")
    if st.button("Clear", use_container_width=True) and mem_id:
        try:
            client.clear_memory(mem_id)
            st.success("Cleared")
        except Exception as e:
            st.error(str(e))
    st.caption("Enable Memory + set Session ID in chat to use.")

# ──────────────────────────────────────────────
# CHAT
# ──────────────────────────────────────────────
if mode == "Chat":
    st.title("Chat")

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "meta" in msg:
                with st.expander("Details"):
                    st.json(msg["meta"])

    if prompt := st.chat_input("Type a message..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages if "meta" not in m]
                    resp = client.chat(
                        provider=chat_provider,
                        model=chat_model_id,
                        messages=msgs,
                        system_prompt=chat_system if chat_system else None,
                        memory=chat_memory,
                        session_id=chat_session if chat_session else None,
                    )
                    text = "".join(c.get("message", {}).get("content", "") for c in resp.get("choices", []))
                    meta = {"provider": resp.get("provider"), "model": resp.get("model"), "usage": resp.get("usage")}
                    st.markdown(text)
                    with st.expander("Details"):
                        st.json(meta)
                    st.session_state.chat_messages.append({"role": "assistant", "content": text, "meta": meta})
                except FreewayClientError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Request failed: {e}")

# ──────────────────────────────────────────────
# CONTINUE CHAT
# ──────────────────────────────────────────────
if mode == "ContinueChat":
    st.title("Continue Chat")
    st.caption("Auto-fallback across providers")

    for msg in st.session_state.continue_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "meta" in msg:
                with st.expander("Details"):
                    st.json(msg["meta"])

    if prompt := st.chat_input("Type a message..."):
        st.session_state.continue_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Trying providers..."):
                try:
                    msgs = [{"role": m["role"], "content": m["content"]} for m in st.session_state.continue_messages if "meta" not in m]
                    resp = client.continue_chat(
                        messages=msgs,
                        system_prompt=cont_system if cont_system else None,
                        memory=cont_memory,
                        session_id=cont_session if cont_session else None,
                        provider_priority=cont_priority if cont_priority else None,
                    )
                    text = "".join(c.get("message", {}).get("content", "") for c in resp.get("choices", []))
                    meta = {"provider": resp.get("provider"), "model": resp.get("model"), "usage": resp.get("usage")}
                    st.markdown(text)
                    st.info(f"Answered by: **{meta['provider']}** / **{meta['model']}**")
                    with st.expander("Details"):
                        st.json(meta)
                    st.session_state.continue_messages.append({"role": "assistant", "content": text, "meta": meta})
                except FreewayClientError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Request failed: {e}")
