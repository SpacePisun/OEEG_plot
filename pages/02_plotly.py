import streamlit as st
from sidebar import render_sidebar
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.express as px
import sys
from pathlib import Path
import os
import datetime
import json

# Добавляем корень проекта в пути импорта
sys.path.append(str(Path(__file__).parent.parent))

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
        /* Уменьшаем отступы для элементов plotly */
        .js-plotly-plot .plotly, .js-plotly-plot .plotly div {
            padding: 0;
            margin: 0;
        }
        /* Уменьшаем верхний отступ у контейнера заголовка */
        .stApp header {
            padding-top: 0;
        }
        /* Уменьшаем нижний отступ у блоков с кнопками */
        div.row-widget.stButton {
            margin-bottom: 0.5rem;
        }
    </style>
""", unsafe_allow_html=True)

# Заголовок страницы и сайдбар
st.title("Анализ графика")
render_sidebar()

# Проверка наличия данных
if "file_content" not in st.session_state:
    st.warning("Сначала загрузите файл на главной странице!")
    st.stop()

# Проверка наличия пути для сохранения данных
if "save_dir" not in st.session_state:
    # Если не установлен путь для сохранения в sidebar, используем директорию проекта
    st.session_state.save_dir = str(Path(__file__).parent.parent)

# Определяем путь для сохранения данных из графика
if "data_save_path" not in st.session_state:
    # Если путь для сохранения не определен, используем директорию из sidebar
    st.session_state.data_save_path = st.session_state.save_dir
    # Создаем директорию, если её нет
    os.makedirs(st.session_state.data_save_path, exist_ok=True)

# Инициализация состояния для хранения границ выбранной области
if "selected_range" not in st.session_state:
    st.session_state.selected_range = {"x_min": None, "x_max": None}

# Подготовка данных
file_text = st.session_state['file_content']
lines = [line.strip() for line in file_text.splitlines() if not line.startswith('#')]

groups = ["AVERAGE", "0[P3]15", "1[F3]16", "2[Cz]12", "3[P4]11",
          "4[F4]10", "5[Fz]32", "6[T3]36", "7[T4]27"]
bands = ["УПП(<0.5Hz)", "Delta(0.5-4)", "Theta(4-7)", "Alpha(8-14)", "Beta(14-30)", "Gamma(30-95)"]

columns = [('Time', ''), ('Marker', '')]
for group in groups:
    for band in bands:
        columns.append((group, band))

data = []
for line in lines:
    parts = line.split()
    if not line[-1].isnumeric(): parts = parts[:-1]
    row = [parts[0], parts[1]] + [float(x) for x in parts[2:]]
    data.append(row)
df = pd.DataFrame(data, columns=pd.MultiIndex.from_tuples(columns))
df[('Time', '')] = pd.to_datetime(df[('Time', '')], format='%H:%M:%S')
start_time = df[('Time', '')].iloc[0]
df[('Seconds', '')] = (df[('Time', '')] - start_time).dt.total_seconds()

available_groups = [g for g in groups if g in df.columns.get_level_values(0)]

# Сохранение выбранной группы в session_state
if 'selected_group' not in st.session_state:
    st.session_state.selected_group = available_groups[0] if available_groups else None

# Создание кнопок в одну строку с минимальным отступом
st.write("Выберите группу:")
cols = st.columns(len(available_groups))
for i, group in enumerate(available_groups):
    with cols[i]:
        if st.button(group, key=f"btn_{group}",
                     use_container_width=True,
                     type="primary" if st.session_state.selected_group == group else "secondary"):
            st.session_state.selected_group = group

selected_group = st.session_state.selected_group

# Отрисовка графика
russian_markers = {'В': 'В', 'О': 'О', 'Э': 'Э', 'Д': 'Д', 'К': 'К', 'И': 'И', 'З': 'З'}

# Создаем график с оптимизированными параметрами
fig = make_subplots(specs=[[{"secondary_y": True}]])

fig.update_layout(
    width=2000,
    height=500,  # Уменьшаем высоту для компактности
    margin=dict(l=40, r=40, t=40, b=40),  # Уменьшаем все отступы
    legend=dict(x=0.98, y=0.98, font=dict(size=10)),  # Уменьшаем шрифт легенды
    title=dict(text=f'{selected_group} - Все полосы частот с маркерами', font=dict(size=14)),  # Уменьшаем заголовок
    xaxis_title='Время записи, секунды',
    xaxis=dict(title_font=dict(size=12)),  # Уменьшаем шрифт оси X
    yaxis=dict(title_font=dict(size=12)),  # Уменьшаем шрифт оси Y
    yaxis2=dict(title_font=dict(size=12))  # Уменьшаем шрифт второй оси Y
)

for band in bands:
    if (selected_group, band) in df.columns:
        y_data = df[(selected_group, band)]
        line_width = 3
        secondary = True if band == "УПП(<0.5Hz)" else False
        fig.add_trace(
            go.Scatter(
                x=df[('Seconds', '')],
                y=y_data,
                mode='lines',
                name=f"{band}",  # Укорачиваем название для компактности
                line=dict(width=line_width)
            ),
            secondary_y=secondary
        )

shapes, annotations = [], []
df[('Marker', '')] = df[('Marker', '')].str.replace('.', '', regex=False)
for idx, row in df.iterrows():
    marker = row[('Marker', '')]
    if marker:
        x_pos = row[('Seconds', '')]
        shapes.append(dict(
            type='line', x0=x_pos, x1=x_pos,
            y0=0, y1=1, yref='paper',
            line=dict(color='red', dash='dash', width=1)
        ))
        annotations.append(dict(
            x=x_pos, y=0.95,
            xref='x', yref='paper',
            text=russian_markers.get(marker, '?'),
            font=dict(color='red', size=12),
            showarrow=False, textangle=-90
        ))

fig.update_layout(
    shapes=shapes,
    annotations=annotations
)
fig.update_yaxes(title_text="Амплитуда ЭЭГ, мкВ", secondary_y=False)
fig.update_yaxes(title_text="Амплитуда УПП, мкВ", secondary_y=True)

# Добавляем callback для отслеживания увеличения (приближения) графика
fig.update_layout(
    updatemenus=[
        dict(
            type="buttons",
            direction="right",
            buttons=[
                dict(
                    label="Сбросить увеличение",
                    method="relayout",
                    args=[{"xaxis.autorange": True, "yaxis.autorange": True}]
                )
            ],
            pad={"r": 10, "t": 10},
            showactive=False,
            x=0.11,
            xanchor="left",
            y=1.1,
            yanchor="top"
        )
    ]
)

# Используем use_container_width=True для адаптивности
plotly_chart = st.plotly_chart(fig, use_container_width=True)


# Функция для получения данных из выбранного диапазона
def get_selected_range_data(df, x_min, x_max, selected_group, bands):
    if x_min is None or x_max is None:
        # Если диапазон не выбран, возвращаем все данные
        return df

    # Фильтруем по выбранному диапазону по оси X (секунды)
    filtered_df = df[(df[('Seconds', '')] >= x_min) & (df[('Seconds', '')] <= x_max)].copy()
    return filtered_df


# Функция для подготовки данных выбранной группы
def prepare_selected_data(df, selected_group, bands, x_min=None, x_max=None):
    # Если указаны диапазоны x_min и x_max, фильтруем данные
    if x_min is not None and x_max is not None:
        df = df[(df[('Seconds', '')] >= x_min) & (df[('Seconds', '')] <= x_max)]

    # Создаем новый DataFrame с нужными колонками
    selected_cols = [('Time', ''), ('Seconds', ''), ('Marker', '')]
    for band in bands:
        if (selected_group, band) in df.columns:
            selected_cols.append((selected_group, band))

    selected_data = df[selected_cols].copy()

    # Преобразуем время в строковый формат для текстового файла
    selected_data[('Time', '')] = selected_data[('Time', '')].dt.strftime('%H:%M:%S')

    return selected_data


# Функция для сохранения данных в текстовый файл
def save_data_to_file(data, selected_group, x_min=None, x_max=None):
    # Создаем имя файла с временной меткой и информацией о диапазоне
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Добавляем информацию о диапазоне в имя файла, если он указан
    range_info = ""
    if x_min is not None and x_max is not None:
        range_info = f"_range_{x_min:.1f}-{x_max:.1f}sec"

    # Если файл был загружен, используем его имя как префикс
    file_prefix = ""
    if "uploaded_name" in st.session_state:
        file_prefix = Path(st.session_state["uploaded_name"]).stem + "_"

    filename = f"{file_prefix}{selected_group}_data{range_info}_{timestamp}.txt"

    # Создаем директорию для файла, если его нет
    if "uploaded_name" in st.session_state:
        base_name = Path(st.session_state["uploaded_name"]).stem
        save_path = Path(st.session_state.save_dir) / base_name
        save_path.mkdir(parents=True, exist_ok=True)
    else:
        save_path = Path(st.session_state.data_save_path)

    file_path = save_path / filename

    # Преобразуем DataFrame в текстовый формат
    header = '\t'.join([f"{col[0]}_{col[1]}" if col[1] else col[0] for col in data.columns])

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"# {header}\n")
        data.to_csv(f, sep='\t', header=False, index=False)

    return str(file_path), filename


# Добавляем элементы для отображения и манипуляции с границами
col1, col2, col3 = st.columns([2, 2, 3])

# Получаем текущие видимые границы из plotly
if selected_group:
    with col1:
        st.write("Выберите диапазон времени (секунды):")
        # Минимальное и максимальное значения для всего графика
        min_seconds = df[('Seconds', '')].min()
        max_seconds = df[('Seconds', '')].max()

        # Получаем значения из sliders или используем мин/макс весь диапазон
        x_min = st.number_input("От:", value=float(min_seconds),
                                min_value=float(min_seconds),
                                max_value=float(max_seconds),
                                step=0.5, format="%.1f")

        x_max = st.number_input("До:", value=float(max_seconds),
                                min_value=float(min_seconds),
                                max_value=float(max_seconds),
                                step=0.5, format="%.1f")

        # Сохраняем выбранный диапазон
        st.session_state.selected_range["x_min"] = x_min
        st.session_state.selected_range["x_max"] = x_max

    with col2:
        st.write("Действия с данными:")
        # Получаем выбранный диапазон
        x_min = st.session_state.selected_range["x_min"]
        x_max = st.session_state.selected_range["x_max"]

        # Значения для отображения пользователю
        if x_min is None or x_max is None or x_min == min_seconds and x_max == max_seconds:
            range_text = "весь диапазон данных"
        else:
            range_text = f"от {x_min:.1f} до {x_max:.1f} сек"

        st.write(f"Выбран диапазон: {range_text}")

        # Подготавливаем данные в соответствии с выбранным диапазоном
        selected_data = prepare_selected_data(df, selected_group, bands, x_min, x_max)

        # Показываем количество точек в выбранном диапазоне
        st.write(f"Количество точек данных: {len(selected_data)}")

        # Добавляем две кнопки: для сохранения в папку и для скачивания
        col_save, col_download = st.columns(2)

        # Кнопка для сохранения данных в папку
        if col_save.button("Сохранить в папку", type="primary"):
            file_path, filename = save_data_to_file(selected_data, selected_group, x_min, x_max)

            # Отображаем полный путь к файлу
            save_dir = Path(file_path).parent
            st.success(f"Данные сохранены в файл: {filename}")
            st.info(f"Путь к файлу: {save_dir}")

        # Кнопка для скачивания данных через браузер
        if col_download.button("Скачать файл", type="secondary"):
            # Временно сохраняем для скачивания
            temp_path = Path(st.session_state.data_save_path) / f"temp_{selected_group}_{x_min:.1f}-{x_max:.1f}.txt"

            # Преобразуем DataFrame в текстовый формат для скачивания
            header = '\t'.join([f"{col[0]}_{col[1]}" if col[1] else col[0] for col in selected_data.columns])
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(f"# {header}\n")
                selected_data.to_csv(f, sep='\t', header=False, index=False)

            # Подготовка данных для скачивания через Streamlit
            with open(temp_path, 'r', encoding='utf-8') as f:
                file_content = f.read()

            # Создаем имя файла для скачивания
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            range_info = f"_range_{x_min:.1f}-{x_max:.1f}sec" if x_min != min_seconds or x_max != max_seconds else ""

            file_prefix = ""
            if "uploaded_name" in st.session_state:
                file_prefix = Path(st.session_state["uploaded_name"]).stem + "_"

            download_filename = f"{file_prefix}{selected_group}_data{range_info}_{timestamp}.txt"

            # Кнопка скачивания
            st.download_button(
                label="Загрузить файл",
                data=file_content,
                file_name=download_filename,
                mime="text/plain"
            )

            # Удаляем временный файл
            try:
                os.remove(temp_path)
            except:
                pass

# Добавление инструкции по использованию
with st.expander("Как использовать приближение графика"):
    st.write("""
    1. Используйте инструменты Plotly для приближения интересующей области:
       - Выделите мышью область для увеличения
       - Используйте колесико мыши для масштабирования
       - Двойной клик для сброса увеличения
    2. После приближения интересующей области, введите соответствующие значения времени в поля "От:" и "До:"
    3. Выберите действие:
       - "Сохранить в папку" - сохраняет данные в папку, указанную в боковой панели (Sidebar)
       - "Скачать файл" - скачивает данные через браузер напрямую

    **Примечание:** Если файл был загружен через главную страницу, данные будут сохранены в подпапку с именем файла 
    внутри директории, указанной в боковой панели (также как сохраняются графики).
    """)