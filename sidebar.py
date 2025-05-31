import streamlit as st
from pathlib import Path


def render_sidebar():
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] {display: none;}
        </style>
        """,
        unsafe_allow_html=True
    )

    with st.sidebar:
        # Навигация
        st.page_link("main.py", label="Главная")
        st.title("Навигация")
        st.page_link("pages/01_matplotlib.py", label="Построение графика")
        st.page_link("pages/02_plotly.py", label="Анализ графика")
        st.page_link("pages/03_meen_sem.py", label="Математический анализ")

        # Единственное поле для пути сохранения
        # Способ 1: Используем key без предварительной инициализации в session_state
        st.text_input(
            "Путь к папке для сохранения",
            value=str(Path.cwd()),  # значение по умолчанию без использования session_state
            key="save_dir",
            help="Укажите абсолютный или относительный путь"
        )

        # Загрузка файла
        st.title("Загрузка файла")
        uploaded_file = st.file_uploader(
            "Выберите текстовый файл",
            type=["txt"]
        )
        if uploaded_file is not None:
            st.session_state["file_content"] = uploaded_file.getvalue().decode("utf-8")
            st.session_state["uploaded_name"] = uploaded_file.name