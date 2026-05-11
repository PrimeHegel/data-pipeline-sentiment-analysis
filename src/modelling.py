import mysql.connector
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

DB_CONFIG = {
    "host": "host.docker.internal",
    "user": "root",
    "password": "root",
    "port": 3307,
    "database": "db_skripsi_hegel",
}


def rating_to_sentiment(rating):
    if rating > 3:
        return "Positif"
    elif rating == 3:
        return "Netral"
    return "Negatif"


def modelling():
    print("Modelling (Naive Bayes)")

    # read cleansed_data
    conn = mysql.connector.connect(**DB_CONFIG)
    df = pd.read_sql("SELECT * FROM data_cleansed", conn)
    conn.close()

    df["target"] = df["rating"].apply(rating_to_sentiment)

    vectorizer = TfidfVectorizer(max_features=5000)
    X = vectorizer.fit_transform(df["review_processed"].values.astype("U"))

    nb = MultinomialNB()
    nb.fit(X, df["target"])

    df["pred_label"] = nb.predict(X)
    df["status"] = df.apply(
        lambda row: "Match" if row["target"] == row["pred_label"] else "Misclassified",
        axis=1,
    )
    accuracy = (df["target"] == df["pred_label"]).mean()

    # insert result to sentiment_result
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("TRUNCATE TABLE sentiment_results")

    query = """
        INSERT INTO sentiment_results
            (brand_name, review_raw, review_processed, rating, sentiment_label, status, accuracy_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    df = df.where(pd.notnull(df), None)
    rows = [
        (
            r.brand_name, r.review_raw, r.review_processed,
            int(r.rating), r.pred_label, r.status, round(accuracy, 4),
        )
        for r in df.itertuples()
    ]
    cursor.executemany(query, rows)
    conn.commit()
    conn.close()

    print(f"Done. Accuracy: {accuracy:.4f} | {len(rows)} rows → sentiment_results.")


if __name__ == "__main__":
    modelling()