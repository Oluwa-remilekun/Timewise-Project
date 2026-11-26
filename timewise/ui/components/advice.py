"""On-demand AI advice panel with per-session caching."""

from collections.abc import Callable, Hashable

import streamlit as st

from timewise.ai.advisor import Advice


def render_advice(
    state_key: str,
    signature: Hashable,
    generate: Callable[[], Advice],
    button_label: str,
) -> None:
    """Render a button that generates advice and keep the result until the data changes.

    ``signature`` identifies the data the advice was generated from; cached advice
    is discarded when it no longer matches, so stale suggestions are never shown
    and the model is only called when the user asks.
    """
    cached = st.session_state.get(state_key)
    if cached and cached["signature"] != signature:
        cached = None

    if st.button(button_label, icon=":material/auto_awesome:", key=f"{state_key}_button"):
        with st.spinner("Thinking..."):
            cached = {"signature": signature, "advice": generate()}
        st.session_state[state_key] = cached

    if not cached:
        return
    advice = cached["advice"]
    st.markdown(advice.text)
    if not advice.is_ai_generated:
        st.caption(f"Showing rule-based tips instead of AI suggestions. {advice.note}")
