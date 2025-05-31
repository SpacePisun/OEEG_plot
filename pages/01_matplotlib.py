import sys
import streamlit as st
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.transforms import offset_copy

# Уменьшаем отступы страницы с помощью CSS
st.set_page_config(page_title="Построение графика", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
        }
        h1 {
            margin-top: 0;
            padding-top: 0;
            margin-bottom: 0.5rem;
        }
        .stButton button {
            padding: 0.15rem 0.5rem;
        }
        div[data-testid="stVerticalBlock"] > div {
            padding-top: 0.25rem;
            padding-bottom: 0.25rem;
        }
        section[data-testid="stSidebar"] {
            padding-top: 1rem;
        }
        /* Принудительно размещаем кнопку в центре */
        div.css-1r6slb0.e1tzin5v0 {
            text-align: center;
            width: 100%;
        }
        /* Кастомный стиль для кнопок каналов */
        .stButton>button[data-testid^="channel_select_"] {
            width: 100%;
            background-color: white;
            color: black;
            border: 2px solid #cccccc;
        }
        .stButton>button[data-testid^="channel_select_"].selected {
            background-color: #007bff;
            color: white;
            border: 2px solid #007bff;
        }
    </style>
""", unsafe_allow_html=True)
from sidebar import render_sidebar

# Заголовок страницы
st.title("Построение графика")
render_sidebar()

# Проверка наличия данных
if 'file_content' not in st.session_state or 'uploaded_name' not in st.session_state:
    st.warning("Сначала загрузите файл на главной странице!")
    st.stop()

# Подготовка папки и имён
file_name = st.session_state['uploaded_name']
base_name = Path(file_name).stem
output_dir = Path(base_name)
output_dir.mkdir(parents=True, exist_ok=True)

# Чтение и подготовка данных
file_text = st.session_state['file_content']
lines = [ln.strip() for ln in file_text.splitlines() if not ln.startswith('#')]
groups = ["AVERAGE", "0[P3]15", "1[F3]16", "2[Cz]12", "3[P4]11",
          "4[F4]10", "5[Fz]32", "6[T3]36", "7[T4]27"]
bands = ["УПП(<0.5Hz)", "Delta(0.5-4)", "Theta(4-7)",
         "Alpha(8-14)", "Beta(14-30)", "Gamma(30-95)"]

columns = [('Time', ''), ('Marker', '')] + [(g, b) for g in groups for b in bands]
data = []
for line in lines:
    parts = line.split()
    if not line[-1].isnumeric(): parts = parts[:-1]
    row = [parts[0], parts[1]] + [float(x) for x in parts[2:]]
    data.append(row)
df = pd.DataFrame(data, columns=pd.MultiIndex.from_tuples(columns))

# Время → секунды
df[('Time', '')] = pd.to_datetime(df[('Time', '')], format='%H:%M:%S')
start = df[('Time', '')].iloc[0]
df[('Seconds', '')] = (df[('Time', '')] - start).dt.total_seconds()

# Цвета
band_colors = {
    "УПП(<0.5Hz)": "#000000",
    "Delta(0.5-4)": "#ff0000",
    "Theta(4-7)": "#7fb310",
    "Alpha(8-14)": "#4f2186",
    "Beta(14-30)": "#009cca",
    "Gamma(30-95)": "#CDA434"
}

# Определение доступных каналов
available = [g for g in groups if (g, bands[0]) in df.columns]



# Инициализация выбранного канала в session_state, если еще не установлен
if 'selected_channel' not in st.session_state:
    st.session_state.selected_channel = available[0] if available else None

# Создание кнопок с улучшенной визуализацией выбора
st.write("Выберите канал:")
cols = st.columns(len(available))

for i, channel in enumerate(available):
    with cols[i]:
        # Создаем уникальный ключ для каждой кнопки
        button_key = f"channel_select_{channel}"

        # Определяем, является ли канал выбранным
        is_selected = channel == st.session_state.selected_channel

        # Создаем кнопку с условным стилем
        if is_selected:
            # Стиль для выбранной кнопки
            st.markdown(f"""
            <style>
            div[data-testid="{button_key}"] > button {{
                background-color: #007bff !important;
                color: white !important;
                border: 2px solid #007bff !important;
            }}
            </style>
            """, unsafe_allow_html=True)

        # Создаем кнопку
        if st.button(
                channel,
                key=button_key,
                use_container_width=True,
                help=f"Выбрать канал {channel}"
        ):
            # Обновляем выбранный канал при клике
            st.session_state.selected_channel = channel
            # Используем st.rerun() вместо experimental_rerun()
            st.rerun()

# Получаем текущий выбранный канал
selected = st.session_state.selected_channel

# Настройка вертикального расстояния между маркерами
st.sidebar.markdown("### Настройки графика")
marker_spacing = st.sidebar.slider("Вертикальное расстояние между маркерами", 1, 10, 3, 1)

# Построение графика с уменьшенными отступами и размерами
plt.rcParams['font.family'] = 'DejaVu Sans'
fig, ax1 = plt.subplots(figsize=(15, 5))  # Уменьшаем высоту с 6 до 5
plt.subplots_adjust(bottom=0.15, top=0.95)  # Уменьшаем отступы графика
ax2 = ax1.twinx()

# Сначала построим графики (все кроме УПП)
for band in bands:
    col = (selected, band)
    if col in df.columns:
        y = df[col]
        c = band_colors.get(band)
        if band != "УПП(<0.5Hz)":
            ax1.plot(df[('Seconds', '')], y, label=band, color=c, linewidth=3, zorder=5)

# Обработка маркеров
# Получаем все уникальные маркеры
markers = df[('Marker', '')].fillna('').astype(str).str.strip().str.replace('.', '').values
seconds = df[('Seconds', '')].values

# Создаем словарь для хранения последних координат маркеров
marker_positions = {}
min_distance = 5  # Минимальное расстояние между метками в секундах

# Сортируем маркеры и их координаты
for x, m in zip(seconds, markers):
    if m:
        # Группируем метки, близкие по времени
        assigned = False
        for pos in list(marker_positions.keys()):
            if abs(x - pos) < min_distance:
                marker_positions[pos].append((x, m))
                assigned = True
                break
        if not assigned:
            marker_positions[x] = [(x, m)]

# Настройка осей и легенды с более компактным размещением
l1, lab1 = ax1.get_legend_handles_labels()
l2, lab2 = ax2.get_legend_handles_labels()
ax1.legend(l1 + l2, lab1 + lab2,
           loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=6, frameon=False, fontsize=9)
ax1.yaxis.set_major_locator(ticker.MultipleLocator(5))  # Фиксированные деления на оси Y
ax1.set_xlim(left=-10)  # фиксируем только нижнюю границу X
ax2.set_xlim(left=-10)
ax1.relim()  # пересчитаем по Y
ax1.autoscale_view()
ax2.relim()
ax2.autoscale_view()
ax1.set_xlabel('Время записи, с', fontsize=10)
ax1.set_ylabel('Амплитуда ЭЭГ, мкВ', fontsize=10)
ax2.set_ylabel('Амплитуда УПП, мкВ', fontsize=10)
plt.title(selected, pad=5)  # Уменьшаем отступ заголовка
plt.grid(True, zorder=1)  # Сетка снизу всех графиков

# Теперь отрисовываем УПП после того, как графики настроены
for band in bands:
    col = (selected, band)
    if col in df.columns and band == "УПП(<0.5Hz)":
        y = df[col]
        c = band_colors.get(band)
        ax2.plot(df[('Seconds', '')], y, label=band, color=c, linewidth=5, zorder=10)

# Увеличиваем верхний предел оси Y для размещения смещенных маркеров
y1_lim = ax1.get_ylim()
ax1.set_ylim(y1_lim[0], y1_lim[1] * 1.2)  # Увеличиваем верхний предел на 20%

# И только после этого отрисуем метки поверх всех графиков
y_top = ax1.get_ylim()[1] * 0.95  # Отступ для верхних меток

# Отрисовка меток с вертикальным смещением и стрелками
for group_x, markers in marker_positions.items():
    # Рисуем вертикальную линию для группы
    ax1.axvline(x=group_x, color='red', linestyle='--', alpha=0.5, zorder=20)

    # Сортируем маркеры по времени для более стабильного отображения
    sorted_markers = sorted(markers, key=lambda m: m[0])

    # Отрисовываем метки для этой группы со смещением вниз по Y если их несколько
    for i, (x, m) in enumerate(sorted_markers):
        if len(sorted_markers) == 1:
            # Если одна метка, просто отображаем ее без указателя
            ax1.text(x, y_top, m,
                     fontsize=12, ha='center', va='top', color='red', rotation=90,
                     backgroundcolor='white', alpha=0.9,
                     zorder=30)  # Увеличиваем zorder для отображения поверх всего
        else:
            # Для нескольких меток смещаем вниз и добавляем указатели
            # Первая метка на самом верху, остальные сдвигаются вниз с отступом
            y_offset = y_top * (1 - i * marker_spacing * 0.03)  # Смещение вниз пропорционально индексу

            # Отрисовываем текстовую метку с высоким zorder
            ax1.text(x, y_offset, m,
                     fontsize=12, ha='center', va='top', color='red', rotation=90,
                     backgroundcolor='white', alpha=0.9,
                     zorder=30)  # Высокий zorder для отображения поверх всего

            # Если это не первая метка, добавляем указатель
            if i > 0:
                # Добавляем стрелку от смещенной метки к вертикальной линии
                ax1.annotate('',
                             xy=(group_x, y_top * 0.9),  # Конец стрелки у вертикальной линии
                             xytext=(x, y_offset * 0.95),  # Начало стрелки у метки
                             arrowprops=dict(arrowstyle='->', color='red', alpha=0.7, linewidth=1.5),
                             zorder=25)  # Высокий zorder для стрелки

plt.tight_layout()

# Отображение графика на всю ширину
st.pyplot(fig)

# Явное создание вертикального блока для кнопки
st.write("")  # Пустая строка для создания вертикального разделения

# Кнопка для сохранения графика, размещенная под графиком
if st.button("Сохранить график", key="save_btn"):
    # Корневая папка, которую ввёл пользователь
    root = Path(st.session_state["save_dir"])
    # Подпапка с базовым именем файла
    dest_dir = root / base_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Полный путь для сохранения
    output_path = dest_dir / f"{selected}.png"

    # Сохраняем фигуру
    fig.savefig(output_path)
    st.success(f"График сохранён: {output_path}")