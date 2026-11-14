"""Visual identity: logo, icon and the custom stylesheet."""

from pathlib import Path

import streamlit as st

_ASSETS = Path(__file__).parent / "assets"
LOGO = str(_ASSETS / "logo.svg")
ICON = str(_ASSETS / "icon.svg")


def apply_styles() -> None:
    st.html(_ASSETS / "styles.css")
