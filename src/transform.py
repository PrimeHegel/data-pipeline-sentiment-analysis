import re

import mysql.connector
import pandas as pd
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

DB_CONFIG = {
    "host": "host.docker.internal",
    "user": "root",
    "password": "root",
    "port": 3307,
    "database": "db_skripsi_hegel",
}

# negation
NEGATION_WORDS = {"tidak", "belum", "kurang", "jangan", "bukan"}

# slang
SLANG_WORDS = ["yg", "klo", "aja", "dah", "deh", "sih", "nya", "pas", "biar", "kan", "dong"]


def build_stopword_set():
    default_stopwords = set(StopWordRemoverFactory().get_stop_words())
    return (default_stopwords - NEGATION_WORDS) | set(SLANG_WORDS)


def clean_text(text, stemmer, stopwords):
    text = re.sub(r"[^a-zA-Z\s]", " ", str(text).lower())
    stemmed = stemmer.stem(text)
    return " ".join(w for w in stemmed.split() if w not in stopwords)


def transform():
    print("--- Transform (Preprocessing) ---")

    conn = mysql.connector.connect(**DB_CONFIG)
    df = pd.read_sql("SELECT * FROM data_raw", conn)

    stemmer = StemmerFactory().create_stemmer()
    stopwords = build_stopword_set()

    df["review_processed"] = df["review_content"].apply(
        lambda text: clean_text(text, stemmer, stopwords)
    )

    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE data_cleansed")

    query = """
        INSERT INTO data_cleansed (brand_name, review_raw, review_processed, rating)
        VALUES (%s, %s, %s, %s)
    """
    df = df.where(pd.notnull(df), None)
    rows = [
        (r.brand_name, r.review_content, r.review_processed, int(r.rating) if r.rating else None)
        for r in df.itertuples()
    ]
    cursor.executemany(query, rows)
    conn.commit()
    conn.close()

    print(f"Done. {len(rows)} rows → data_cleansed.")


if __name__ == "__main__":
    transform()
