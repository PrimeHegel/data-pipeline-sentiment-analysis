import os

import mysql.connector
import pandas as pd

DB_CONFIG = {
    "host": "host.docker.internal",
    "user": "root",
    "password": "root",
    "port": 3307,
    "database": "db_skripsi_hegel",
}

OFFSET_FILE = "data/offset.txt"
CHUNK_SIZE = 500
MAX_ROWS = 3000


def read_offset():
    if not os.path.exists(OFFSET_FILE):
        return 0
    with open(OFFSET_FILE, "r") as f:
        content = f.read().strip()
    return int(content) if content else 0


def write_offset(value):
    with open(OFFSET_FILE, "w") as f:
        f.write(str(value))


def load_source_data():
    df_reviews = pd.read_csv("data/20191002-reviews.csv")
    df_items = pd.read_csv("data/20191002-items.csv")

    df_reviews["itemId"] = df_reviews["itemId"].astype(str).str.replace(".0", "", regex=False)
    df_items["itemId"] = df_items["itemId"].astype(str).str.replace(".0", "", regex=False)

    items_map = df_items[["itemId", "brandName"]].drop_duplicates(subset=["itemId"])
    df = pd.merge(df_reviews, items_map, on="itemId", how="left")

    df = df[(df["category"] == "beli-harddisk-eksternal") & (df["reviewContent"].notna())]
    df = df.drop_duplicates(subset=["itemId", "reviewContent"])
    return df.head(MAX_ROWS)


def extract():
    print("--- Extract (Incremental) ---")

    offset = read_offset()
    df_full = load_source_data()

    if offset >= len(df_full):
        raise ValueError(
            "Semua 3000 data sudah selesai diproses. Silakan matikan DAG Airflow."
        )

    df_chunk = df_full.iloc[offset : offset + CHUNK_SIZE]

    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    if offset == 0:
        print("Batch pertama — truncate data_raw.")
        cursor.execute("TRUNCATE TABLE data_raw")

    df_chunk = df_chunk.where(pd.notnull(df_chunk), None)
    query = """
        INSERT INTO data_raw
            (item_id, category, reviewer_name, rating, review_title,
             review_content, bought_date, client_type, retrieved_date, brand_name)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    rows = [
        (
            str(r.itemId), r.category, r.name,
            int(r.rating) if r.rating else None,
            r.reviewTitle, r.reviewContent,
            r.boughtDate, r.clientType, r.retrievedDate, r.brandName,
        )
        for r in df_chunk.itertuples()
    ]
    cursor.executemany(query, rows)
    conn.commit()
    conn.close()

    write_offset(offset + CHUNK_SIZE)
    print(f"Done. Rows {offset}–{offset + CHUNK_SIZE} → data_raw ({len(rows)} inserted).")


if __name__ == "__main__":
    extract()