import io
from io import BytesIO
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from sidebar import render_sidebar
import streamlit as st

# ---- Настройка страницы ----
st.set_page_config(
    page_title="Построение графика MEAN±SEM",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("Математический анализ — MEAN ± SEM")


# ---- Добавление кэширования данных ----
@st.cache_data
def parse_data(file_text, groups, bands):
    lines = [line.strip() for line in file_text.splitlines()
             if not line.startswith("#") and line.strip()]

    columns = [("Time", ""), ("Marker", "")]
    for g in groups:
        for b in bands:
            columns.append((g, b))

    data = []
    for line in lines:
        parts = line.split()
        if not parts[-1].replace(".", "", 1).isdigit():
            parts = parts[:-1]
        row = [parts[0], parts[1]] + [float(x) for x in parts[2:]]
        data.append(row)

    df = pd.DataFrame(data, columns=pd.MultiIndex.from_tuples(columns))
    df[("Time", "")] = pd.to_datetime(df[("Time", "")], format="%H:%M:%S")
    start = df[("Time", "")].iloc[0]
    df[("Seconds", "")] = (df[("Time", "")] - start).dt.total_seconds()

    cols = list(df.columns)
    cols.remove(("Seconds", ""))
    idx = cols.index(("Time", "")) + 1
    cols.insert(idx, ("Seconds", ""))
    df = df[cols]
    return df


@st.cache_data
def calculate_mean_sem(df, groups, bands, window_size):
    n = len(df)
    block_idx = np.arange(n) // window_size
    block_groups = df.groupby(block_idx).groups

    block_times = []
    template = []
    for g in groups:
        mean_block = pd.DataFrame(np.nan, index=df.index, columns=df[g].columns)
        sem_block = pd.DataFrame(np.nan, index=df.index, columns=df[g].columns)
        for b in df[g].columns:
            for blk, idxs in block_groups.items():
                mean_val = df[g][b].loc[idxs].mean()
                sem_val = df[g][b].loc[idxs].sem(ddof=1)
                last_i = idxs[-1]
                mean_block.at[last_i, b] = mean_val
                sem_block.at[last_i, b] = sem_val
                # собираем время конца блока только при первом канале
                if g == groups[0] and b == df[g].columns[0]:
                    block_times.append(df[("Seconds", "")].iloc[last_i])

        mean_block.columns = pd.MultiIndex.from_tuples([(g, f"MEAN_{b}") for b in mean_block.columns])
        sem_block.columns = pd.MultiIndex.from_tuples([(g, f"SEM_{b}") for b in sem_block.columns])
        orig = df[g].copy()
        orig.columns = pd.MultiIndex.from_tuples([(g, b) for b in orig.columns])
        template.append(pd.concat([mean_block, sem_block, orig], axis=1))

    # Исправляем эту строку - создаем правильный MultiIndex с 2 уровнями
    time_sec_marker = pd.concat([
        df[("Time", "")],
        df[("Seconds", "")],
        df[("Marker", "")]
    ], axis=1)
    time_sec_marker.columns = pd.MultiIndex.from_tuples([
        ("Time", ""),
        ("Seconds", ""),
        ("Marker", "")
    ])

    df_final = pd.concat([time_sec_marker] + template, axis=1)
    mean_sem_cols = [col for col in df_final.columns if col[1].startswith("MEAN_") or col[1].startswith("SEM_")]

    # Здесь тоже исправляем - явно создаем MultiIndex
    time_sec_marker_ms = pd.concat([
        df_final[("Time", "")],
        df_final[("Seconds", "")],
        df_final[("Marker", "")]
    ], axis=1)
    time_sec_marker_ms.columns = pd.MultiIndex.from_tuples([
        ("Time", ""),
        ("Seconds", ""),
        ("Marker", "")
    ])

    df_mean_sem = pd.concat([time_sec_marker_ms, df_final[mean_sem_cols]], axis=1)
    return df_final, df_mean_sem, block_times


@st.cache_data
def create_plot(df_clean, block_times, selected, bands, show_sem):
    # Словарь цветов для разных частотных диапазонов
    band_colors = {
        "УПП(<0.5Hz)": "#000000",
        "Delta(0.5-4)": "#ff0000",
        "Theta(4-7)": "#7fb310",
        "Alpha(8-14)": "#4f2186",
        "Beta(14-30)": "#009cca",
        "Gamma(30-95)": "#CDA434"
    }
    x = np.array(block_times)

    # Создаем фигуру с двумя осями (для разных диапазонов)
    fig, ax1 = plt.subplots(figsize=(15, 6))
    ax2 = ax1.twinx()

    # Построение графиков для каждого частотного диапазона
    for band in bands:
        mean_col = (selected, f"MEAN_{band}")
        sem_col = (selected, f"SEM_{band}")

        # Пропускаем, если колонка отсутствует
        if mean_col not in df_clean.columns:
            continue

        # Фильтруем NaN значения
        df_subset = df_clean[[mean_col, sem_col]].dropna()
        y_vals = df_subset[mean_col].values

        # Используем соответствующие x-координаты
        x_subset = x[df_subset.index]

        # Выбираем ось в зависимости от диапазона
        ax = ax2 if band == "УПП(<0.5Hz)" else ax1

        # Рисуем линию графика
        ax.plot(x_subset, y_vals, label=band, color=band_colors[band],
                linewidth=5 if band == "УПП(<0.5Hz)" else 3)

        # Добавляем погрешности, если включено
        if show_sem and sem_col in df_clean.columns:
            sem_vals = df_subset[sem_col].values
            ax.errorbar(x_subset, y_vals, yerr=sem_vals, ecolor=band_colors[band],
                        elinewidth=1.5, capsize=3, linestyle='', alpha=0.7)

    # Добавление маркеров
    markers = df_clean[("Marker", "")].fillna('').astype(str).str.strip().values
    for xi, mi in zip(x, markers):
        if mi:
            ax1.axvline(x=xi, color='red', linestyle='--', alpha=0.5)
            ax1.text(xi, ax1.get_ylim()[1] * 0.95, mi,
                     fontsize=10, ha='center', va='top', rotation=90,
                     backgroundcolor='white', color='red')

    # Настройка легенды
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=6, frameon=False)

    # Настройка осей и сетки
    ax1.yaxis.set_major_locator(ticker.MultipleLocator(5))
    ax1.set_xlabel('Время записи, с')
    ax1.set_ylabel('Амплитуда ЭЭГ, мкВ')
    ax2.set_ylabel('Амплитуда УПП, мкВ')
    plt.grid(True)
    plt.tight_layout()

    # Установка границ осей
    ax1.set_xlim(0, x.max())
    ax2.set_xlim(ax1.get_xlim())

    return fig


# Функция для создания DataFrame только с MEAN (без SEM)
def create_mean_only_df(df_clean):
    # Исходные колонки временных меток
    time_cols = [("Time", ""), ("Seconds", ""), ("Marker", "")]
    # Только MEAN колонки (без SEM)
    mean_cols = [col for col in df_clean.columns if col[1].startswith("MEAN_")]

    # Создаем новый DataFrame
    return df_clean[time_cols + mean_cols].copy()


# sidebar и загрузка
render_sidebar()
if "file_content" not in st.session_state or "uploaded_name" not in st.session_state:
    st.warning("Сначала загрузите файл на главной странице!")
    st.stop()
if "save_dir" not in st.session_state:
    # По умолчанию: текущая директория приложения
    st.session_state["save_dir"] = str(Path.cwd())

# Инициализация переменных сессии
if "show_sem" not in st.session_state:
    st.session_state.show_sem = False
if "selected_group" not in st.session_state:
    st.session_state.selected_group = None
if "processing_started" not in st.session_state:
    st.session_state.processing_started = False

# Основные переменные
file_name = st.session_state["uploaded_name"]
base_name = Path(file_name).stem
output_dir = Path(base_name)
output_dir.mkdir(parents=True, exist_ok=True)

# Параметры обработки
groups = ["AVERAGE", "0[P3]15", "1[F3]16", "2[Cz]12", "3[P4]11", "4[F4]10", "5[Fz]32", "6[T3]36", "7[T4]27"]
bands = ["УПП(<0.5Hz)", "Delta(0.5-4)", "Theta(4-7)", "Alpha(8-14)", "Beta(14-30)", "Gamma(30-95)"]

# Интерфейс настроек ПЕРЕД обработкой
st.header("Настройки обработки")
window_size = st.number_input("Расчет среднего и ошибки среднего по следующим значениям",
                              min_value=1, value=10, step=1, format="%d")

# КНОПКА ЗАПУСКА ОБРАБОТКИ
st.markdown("---")
if st.button("🚀 Запустить обработку данных", type="primary", key="start_processing"):
    st.session_state.processing_started = True
    st.rerun()

# Проверяем, была ли начата обработка
if not st.session_state.processing_started:
    st.info("Настройте параметры выше и нажмите кнопку 'Запустить обработку данных' для начала анализа.")
    st.stop()

# ========== ОБРАБОТКА НАЧИНАЕТСЯ ТОЛЬКО ПОСЛЕ НАЖАТИЯ КНОПКИ ==========

st.markdown("---")
st.header("Обработка данных")

# Парсинг и предобработка
with st.spinner('Загрузка и парсинг данных...'):
    df = parse_data(st.session_state["file_content"], groups, bands)
    df[("Marker", "")] = df[("Marker", "")].astype(str).str.replace('.', '', regex=False)

# Расчет MEAN и SEM
with st.spinner('Расчёт MEAN и SEM...'):
    df_final, df_mean_sem, block_times = calculate_mean_sem(df, groups, bands, window_size)

# Фильтрация данных
with st.spinner('Фильтрация и очистка данных...'):
    # Получаем список колонок MEAN/SEM
    mean_sem_cols = [
        col for col in df_mean_sem.columns
        if col[1].startswith("MEAN_") or col[1].startswith("SEM_")
    ]

    # Столбец с маркерами
    marker_col = ("Marker", "")

    # Сначала перенесем маркеры из строк без данных в следующие непустые строки
    df_with_moved_markers = df_mean_sem.copy()
    pending_markers = []
    for i in range(len(df_with_moved_markers)):
        row_has_data = df_with_moved_markers.loc[i, mean_sem_cols].notna().any()
        current_marker = df_with_moved_markers.at[i, marker_col]

        # Если есть отложенные маркеры и текущая строка имеет данные
        if pending_markers and row_has_data:
            # Объединяем все отложенные маркеры только с пробелом
            combined_pending_markers = " ".join([m.strip() for m in pending_markers])

            # Если в текущей строке уже есть маркер, объединяем их
            if pd.notna(current_marker) and str(current_marker).strip():
                current_marker_clean = str(current_marker).strip()
                df_with_moved_markers.at[i, marker_col] = f"{combined_pending_markers} {current_marker_clean}"
            else:
                df_with_moved_markers.at[i, marker_col] = combined_pending_markers

            pending_markers = []  # Очищаем список отложенных маркеров

        # Если в текущей строке есть маркер, но нет данных
        elif pd.notna(current_marker) and str(current_marker).strip() and not row_has_data:
            pending_markers.append(str(current_marker).strip())
            df_with_moved_markers.at[i, marker_col] = None  # Очищаем текущий маркер

    # Маска: есть хотя бы одно значение в MEAN/SEM колонках
    mask = df_with_moved_markers[mean_sem_cols].notna().any(axis=1)

    # Применяем маску для удаления пустых строк
    df_clean = df_with_moved_markers.loc[mask].reset_index(drop=True)

st.success("✅ Обработка данных завершена успешно!")

# Отображение таблицы
st.header("Таблица MEAN и SEM")
mean_disp = df_clean.copy()
mean_disp[("Time", "")] = mean_disp[("Time", "")].dt.strftime("%H:%M:%S")
st.dataframe(mean_disp)

# Создаем две колонки для кнопок сохранения
col1, col2 = st.columns(2)

# Сохранение MEAN+SEM в Excel
if col1.button("Сохранить таблицу MEAN+SEM в Excel", key="save_mean_sem_btn"):
    masked_df = df_clean.copy()
    dest_root = Path(st.session_state['save_dir']) / base_name
    dest_root.mkdir(parents=True, exist_ok=True)
    masked_path = dest_root / f"{base_name}_MEAN_SEM_{window_size}.xlsx"
    with pd.ExcelWriter(masked_path, engine='xlsxwriter', datetime_format='hh:mm:ss') as writer:
        masked_df.to_excel(writer, sheet_name='MEAN_SEM', index=True)
    st.success(f"Файл с MEAN+SEM сохранён в: {masked_path}")

# Сохранение только MEAN в Excel
if col2.button("Сохранить таблицу только MEAN в Excel", key="save_mean_only_btn"):
    mean_only_df = create_mean_only_df(df_clean)
    dest_root = Path(st.session_state['save_dir']) / base_name
    dest_root.mkdir(parents=True, exist_ok=True)
    mean_path = dest_root / f"{base_name}_MEAN_ONLY_{window_size}.xlsx"
    with pd.ExcelWriter(mean_path, engine='xlsxwriter', datetime_format='hh:mm:ss') as writer:
        mean_only_df.to_excel(writer, sheet_name='MEAN_ONLY', index=True)
    st.success(f"Файл только с MEAN сохранён в: {mean_path}")

# Выбор группы
st.header("Выберите группу для графика")
available_groups = [g for g in groups if (g, f"MEAN_{bands[0]}") in df_clean.columns]
cols = st.columns(len(available_groups))
for i, col in enumerate(cols):
    grp = available_groups[i]

    # Определяем стиль кнопки
    button_type = "primary" if grp == st.session_state.selected_group else "secondary"

    if col.button(grp, key=f"btn_{grp}", type=button_type):
        st.session_state.selected_group = grp
        st.rerun()

# Переключатель SEM
if st.button('Показать погрешности' if not st.session_state.show_sem else 'Скрыть погрешности', key='toggle_sem_btn'):
    st.session_state.show_sem = not st.session_state.show_sem
    st.rerun()

# Построение графика
if st.session_state.selected_group:
    selected = st.session_state.selected_group
    st.header(f"{selected} — {'MEAN + SEM' if st.session_state.show_sem else 'только MEAN'}")
    with st.spinner('Построение графика...'):
        fig = create_plot(df_clean, block_times, selected, bands, st.session_state.show_sem)
        st.pyplot(fig)

    # Сохранение/скачивание
    suffix = f"{selected}_mean_sem_{window_size}" if st.session_state.show_sem else f"{selected}_mean_{window_size}"
    output_file = output_dir / f"{suffix}.png"

    # Сохранение графика в пользовательскую папку
    if st.button("Сохранить график в папку", key="save_btn"):
        root = Path(st.session_state["save_dir"] or ".")
        dest_dir = root / base_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        output_path = dest_dir / f"{suffix}.png"
        fig.savefig(output_path)
        st.success(f"График сохранён в: {output_path}")
else:
    st.info("Выберите канал для построения графика")