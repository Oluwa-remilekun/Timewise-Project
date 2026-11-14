"""Gradient banner shown at the top of each page."""

import streamlit as st


def render_page_header(title: str, subtitle: str, highlight: str | None = None) -> None:
    with st.container(key="hero"):
        st.title(title)
        st.markdown(subtitle)
        if highlight:
            st.markdown(highlight)
