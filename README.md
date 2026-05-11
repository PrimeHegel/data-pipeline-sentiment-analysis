# Sentiment Analysis Pipeline — Hard Disk Eksternal

End-to-end data pipeline untuk analisis sentimen ulasan produk hard disk eksternal dari Tokopedia (dataset Kaggle). Pipeline dijalankan secara incremental menggunakan Apache Airflow, data disimpan di MySQL, dan hasil divisualisasikan lewat Streamlit dashboard.

---

## Architecture

```
Kaggle CSV (reviews + items)
        │
        ▼
  [ extract.py ]   ──→  MySQL: data_raw        (incremental, 500 rows/batch)
        │
        ▼
  [ transform.py ] ──→  MySQL: data_cleansed   (Sastrawi stemming + stopword removal)
        │
        ▼
  [ modelling.py ] ──→  MySQL: sentiment_results (TF-IDF + Multinomial Naive Bayes)
        │
        ▼
  [ app.py ]             Streamlit Dashboard    (real-time dari MySQL)
```

Orchestration oleh **Apache Airflow** (CeleryExecutor), berjalan di Docker.

---

## Tech Stack

| Layer | Tools |
|---|---|
| Orchestration | Apache Airflow 2.8 (Docker) |
| Storage | MySQL 8 |
| Processing | Python, Pandas, Sastrawi |
| ML | scikit-learn (TF-IDF + Multinomial Naive Bayes) |
| Dashboard | Streamlit, Plotly |
| Infrastructure | Docker Compose |

---

## Dataset

- Source: [Lazada Indonesian Reviews — Kaggle](https://www.kaggle.com/datasets/grikomsn/lazada-indonesian-reviews)
- File: `20191002-reviews.csv` + `20191002-items.csv`
- Filtered: kategori `beli-harddisk-eksternal`, 3.000 data teratas
- Label sentimen diturunkan dari rating: **Positif** (>3), **Netral** (=3), **Negatif** (<3)

---

## Project Structure

```
Data Flow/
├── app.py                  # Streamlit dashboard
├── dags/
│   └── dag_airflow.py      # Airflow DAG definition
├── src/
│   ├── extract.py          # Load & insert CSV → data_raw (incremental)
│   ├── transform.py        # Text preprocessing → data_cleansed
│   ├── modelling.py        # Naive Bayes training & prediction → sentiment_results
│   └── db_setup.py         # Schema initialization
├── data/
│   ├── 20191002-reviews.csv
│   ├── 20191002-items.csv
│   └── offset.txt          # State file untuk incremental loading
├── docker-compose.yaml
├── requirements.txt
└── .env
```

---

## Setup & Running

### Prerequisites
- Docker Desktop
- Python 3.10+
- MySQL

### 1. Initialize Database Schema

```bash
python src/db_setup.py
```

### 2. Start Airflow + Services

```bash
# Copy environment config
cp .env.example .env

# Start all services (Airflow, Redis, PostgreSQL)
docker-compose up -d

# Wait ~2 minutes for services to be healthy
docker-compose ps
```

### 3. Trigger the Pipeline

Buka Airflow UI di `http://localhost:8080` (user: `airflow`, pass: `airflow`).

Aktifkan dan trigger DAG `sentiment_analysis_express`. Pipeline akan berjalan otomatis setiap 2 menit, memproses 500 baris per eksekusi hingga semua 3.000 data selesai.

### 4. Run Dashboard

```bash
streamlit run app.py
```

Dashboard akan terbuka di `http://localhost:8501`.

---

## Pipeline Detail

### Extract (Incremental)
- Membaca dua file CSV (reviews + items), merge berdasarkan `itemId`
- Filter kategori hard disk eksternal, dedup, ambil 3.000 data pertama
- Insert per-batch 500 baris ke `data_raw`, state disimpan di `data/offset.txt`
- Batch pertama akan truncate tabel untuk clean start

### Transform (Preprocessing)
- Lowercase + remove non-alpha characters
- Stemming menggunakan Sastrawi
- Stopword removal — kata negasi (`tidak`, `belum`, `kurang`, dll.) dipertahankan
- Hasil disimpan ke `data_cleansed`

### Modelling (Naive Bayes)
- Feature extraction: TF-IDF (max 5.000 features)
- Classifier: Multinomial Naive Bayes
- Klasifikasi sentimen menggunakan unsupervised labelling dengan acuan rating bintang sebagai ground truth
- Status tiap row (`Match` / `Misclassified`) dan accuracy score disimpan ke `sentiment_results`

---

## Dashboard Features

- **KPI Cards**: total review, rata-rata rating, jumlah data netral, akurasi model
- **Donut Chart**: distribusi sentimen (Positif / Netral / Negatif)
- **Bar Chart**: perbandingan sentimen per brand (top 10)
- **Brand Insight**: brand dengan ulasan positif & negatif terbanyak
- **Filter**: pencarian keyword, filter per brand, filter per sentimen
- **Live Auto-Refresh**: opsional, refresh setiap 3 detik dari MySQL

---

## Notes

- Pipeline ini menggunakan automated rule-based labelling (berdasarkan rating bintang) — ground truth diturunkan dari rating bintang, bukan anotasi manual.
- Misclassified rows umumnya merupakan *noisy labels*: ulasan dengan rating tinggi tapi berisi keluhan, atau sebaliknya.
