
from pathlib import Path

import streamlit as st

#Настройки страницы
st.set_page_config(
    page_title="Загрузка файла",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Скрываем стандартную навигацию
st.markdown("""
    <style>
      /* Прячем автоматически сгенерированные ссылки на файлы */
      div[data-testid="stSidebarNav"] { display: none; }
      /* Убираем «View more/View less» в новом API навигации */
      [data-testid="stSidebarNavItems"] { max-height: none; }
    </style>
    """, unsafe_allow_html=True)

# --- Сайдбар: собственное меню ---
with st.sidebar:
    st.title("Навигация")
    # Ссылки на нумерованные страницы
    st.page_link("pages/01_matplotlib.py", label="Построение графика")  # Только имя файла из папки pages
    st.page_link("pages/02_plotly.py", label="Анализ графика")
    st.page_link("pages/03_meen_sem.py", label="Математический анализ")

    # Секция загрузки файла
    st.title("Загрузка файла")
    uploaded_file = st.file_uploader(
        "Выберите текстовый файл",
        type=["txt"]
    )

# --- Логика загрузки файла ---
if 'uploaded_file' in locals() and uploaded_file is not None:
    content = uploaded_file.getvalue().decode("utf-8")
    st.session_state['file_content'] = content
    st.session_state['uploaded_name'] = uploaded_file.name

    base_name = Path(uploaded_file.name).stem
    output_dir = Path(base_name)
    output_dir.mkdir(parents=True, exist_ok=True)

    st.success(f"Файл «{uploaded_file.name}» загружен и готов к анализу.")

# --- Основной контент Main ---
st.title("Добро пожаловать!")
st.write(
    "В этом приложении вы можете загружать текстовые файлы и переходить к разделам "
    "Построение графика, Анализ графика и Математический анализ через меню слева."
)
