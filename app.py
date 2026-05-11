import time

import matplotlib.pyplot as plt
import mysql.connector
import pandas as pd
import plotly.express as px
import streamlit as st
from wordcloud import WordCloud

st.set_page_config(
    page_title="Dashboard Sentimen Hard Disk",
    page_icon="💾",
    layout="wide",
)

st.markdown("""
    <style>
    .metric-card {
        background-color: #1E293B;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        text-align: center;
        border: 1px solid #334155;
    }
    .metric-card h3 {
        color: #94A3B8 !important;
        font-size: 1.1rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    .metric-card h2 {
        color: #38BDF8 !important;
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data():
    try:
        conn = mysql.connector.connect(
            host="127.0.0.1",
            port=3307,
            user="root",
            password="root",
            database="db_skripsi_hegel",
            connection_timeout=5,
        )
        query = """
            SELECT brand_name, review_raw, review_processed, rating,
                   sentiment_label AS pred_label, status, accuracy_score AS accuracy
            FROM sentiment_results
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df, "mysql"
    except Exception:
        try:
            df = pd.read_csv("data/temp_results.csv")
            if "pred_label" not in df.columns and "sentiment_label" in df.columns:
                df = df.rename(columns={"sentiment_label": "pred_label"})
            if "accuracy" not in df.columns and "accuracy_score" in df.columns:
                df = df.rename(columns={"accuracy_score": "accuracy"})
            return df, "csv"
        except Exception:
            return pd.DataFrame(), "empty"


df, data_source = load_data()

if data_source == "empty" or df.empty:
    st.warning("⏳ Pipeline Airflow belum berjalan. Tabel `sentiment_results` masih kosong.")
    st.info("**Langkah:** Hidupkan Docker → Buka Airflow UI → Trigger DAG `sentiment_analysis_express`")
    st.stop()


# --- Sidebar ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/1150/1150626.png", width=100)
st.sidebar.title("Filter Data")

if data_source == "mysql":
    st.sidebar.success("✅ Data: MySQL (Real-time)")
else:
    st.sidebar.warning("⚠️ Data: CSV (MySQL offline)")

search_query = st.sidebar.text_input("🔍 Cari Kata Kunci Keluhan/Pujian", placeholder="Ketik kata (contoh: lambat)")

brand_list = ["Semua Brand"] + list(df["brand_name"].dropna().unique())
selected_brand = st.sidebar.selectbox("Pilih Brand", brand_list)

sentiment_list = ["Semua Sentimen", "Positif", "Netral", "Negatif"]
selected_sentiment = st.sidebar.radio("Pilih Hasil Sentimen", sentiment_list)

st.sidebar.markdown("---")
auto_refresh = st.sidebar.checkbox("🔄 Aktifkan Live Auto-Refresh")


# --- Filter ---
df_filtered = df.copy()

if search_query:
    df_filtered = df_filtered[df_filtered["review_raw"].str.contains(search_query, case=False, na=False)]
if selected_brand != "Semua Brand":
    df_filtered = df_filtered[df_filtered["brand_name"] == selected_brand]
if selected_sentiment != "Semua Sentimen":
    df_filtered = df_filtered[df_filtered["pred_label"] == selected_sentiment]


# --- Header ---
st.title("Dashboard Analisis Sentimen Eksternal Hard Disk")
st.markdown("Hasil analisis sentimen menggunakan algoritma **Naive Bayes** — 3 kelas: Positif, Netral, Negatif.")
st.markdown("---")


# --- KPI Cards ---
total_reviews = len(df_filtered)
avg_rating = df_filtered["rating"].mean() if total_reviews > 0 else 0
neutral_count = len(df_filtered[df_filtered["pred_label"] == "Netral"]) if total_reviews > 0 else 0
model_accuracy = df["accuracy"].iloc[0] * 100 if not df.empty else 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="metric-card"><h3>Total Review Ditemukan</h3><h2>{total_reviews:,}</h2></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><h3>Rata-rata Rating</h3><h2>{avg_rating:.1f} / 5.0</h2></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><h3>Data Netral</h3><h2>{neutral_count:,}</h2></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="metric-card"><h3>Akurasi Model</h3><h2>{model_accuracy:.1f}%</h2></div>', unsafe_allow_html=True)

st.write("")
st.write("")

if total_reviews == 0:
    st.warning("Tidak ada review yang cocok dengan filter kamu.")
    st.stop()


# --- Charts ---
color_map = {"Positif": "#2ecc71", "Netral": "#f1c40f", "Negatif": "#e74c3c"}

fig_col1, fig_col2 = st.columns(2)

with fig_col1:
    st.subheader("Distribusi Sentimen (Positif vs Netral vs Negatif)")
    sentiment_counts = df_filtered["pred_label"].value_counts().reset_index()
    sentiment_counts.columns = ["Sentimen", "Jumlah"]
    fig_pie = px.pie(
        sentiment_counts,
        names="Sentimen",
        values="Jumlah",
        hole=0.4,
        color="Sentimen",
        color_discrete_map=color_map,
    )
    fig_pie.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig_pie, use_container_width=True)

with fig_col2:
    st.subheader("Perbandingan Sentimen per Brand")
    top_brands = df_filtered["brand_name"].value_counts().head(10).index
    brand_sentiment = (
        df_filtered[df_filtered["brand_name"].isin(top_brands)]
        .groupby(["brand_name", "pred_label"])
        .size()
        .reset_index(name="Jumlah")
    )
    fig_bar = px.bar(
        brand_sentiment,
        x="brand_name",
        y="Jumlah",
        color="pred_label",
        barmode="group",
        color_discrete_map=color_map,
        labels={"brand_name": "Brand", "Jumlah": "Jumlah Review"},
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")


# --- Brand Insight ---
st.subheader("🏆 Insight Sentimen Brand")

if "brand_name" in df_filtered.columns and "pred_label" in df_filtered.columns:
    col_insight1, col_insight2 = st.columns(2)

    pos_df = df_filtered[df_filtered["pred_label"] == "Positif"]
    neg_df = df_filtered[df_filtered["pred_label"] == "Negatif"]

    top_pos_brand = pos_df["brand_name"].value_counts().idxmax() if not pos_df.empty else "-"
    top_pos_count = pos_df["brand_name"].value_counts().max() if not pos_df.empty else 0

    top_neg_brand = neg_df["brand_name"].value_counts().idxmax() if not neg_df.empty else "-"
    top_neg_count = neg_df["brand_name"].value_counts().max() if not neg_df.empty else 0

    with col_insight1:
        st.success(f"**Brand Terfavorit (Positif Terbanyak)**\n\n# {top_pos_brand} \n*{top_pos_count} Ulasan Positif*")
    with col_insight2:
        st.error(f"**Brand Paling Banyak Keluhan (Negatif Terbanyak)**\n\n# {top_neg_brand} \n*{top_neg_count} Ulasan Negatif*")
else:
    st.warning("Data tidak cukup untuk menampilkan insight brand.")

st.markdown("---")


# --- Detail Table ---
st.subheader("📋 Detail Data Review Asli")

display_cols = ["brand_name", "rating", "review_raw", "pred_label", "status"]
display_cols = [c for c in display_cols if c in df_filtered.columns]
st.dataframe(df_filtered[display_cols], use_container_width=True, height=400)


# --- Misclassified Table ---
st.subheader("⚠️ Tabel Analisis Misclassified")

if "status" in df_filtered.columns:
    df_misc = df_filtered[df_filtered["status"] == "Misclassified"]
    if not df_misc.empty:
        st.dataframe(df_misc[display_cols], use_container_width=True, height=300)
    else:
        st.info("Tidak ada data yang misclassified berdasarkan filter saat ini.")
else:
    st.warning("Kolom 'status' tidak ditemukan pada data.")

st.caption(
    "Catatan: Misclassified sering muncul pada 'noisy labels' — "
    "ulasan dengan rating tinggi tapi berisi keluhan atau pertanyaan."
)
st.caption("Dashboard dibuat menggunakan Streamlit dan Python.")


# --- Auto-refresh ---
if auto_refresh:
    time.sleep(3)
    st.rerun()
