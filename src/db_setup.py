import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "port": 3307
}

def initialize_database():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Initialize schema
        cursor.execute("CREATE DATABASE IF NOT EXISTS db_skripsi_hegel")
        cursor.execute("USE db_skripsi_hegel")

        # Drop existing tables for a clean slate
        tables_to_drop = ["sentiment_results", "data_cleansed", "data_raw"]
        for table in tables_to_drop:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")

        # 1. Raw extracted data (output dari extract.py)
        cursor.execute("""
            CREATE TABLE data_raw (
                id INT AUTO_INCREMENT PRIMARY KEY,
                item_id VARCHAR(50),
                category VARCHAR(100),
                reviewer_name VARCHAR(255),
                rating INT,
                review_title TEXT,
                review_content TEXT,
                bought_date VARCHAR(50),
                client_type VARCHAR(50),
                retrieved_date VARCHAR(50),
                brand_name VARCHAR(100)
            )
        """)

        # 2. Cleansed/preprocessed data (output dari transform.py)
        cursor.execute("""
            CREATE TABLE data_cleansed (
                id INT AUTO_INCREMENT PRIMARY KEY,
                brand_name VARCHAR(100),
                review_raw TEXT,
                review_processed TEXT,
                rating INT,
                category VARCHAR(50) DEFAULT 'Hard Disk'
            )
        """)

        # 3. Model results (output dari modelling.py)
        cursor.execute("""
            CREATE TABLE sentiment_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                brand_name VARCHAR(100),
                review_raw TEXT,
                review_processed TEXT,
                rating INT,
                sentiment_label VARCHAR(20),
                status VARCHAR(50),
                accuracy_score FLOAT
            )
        """)

        print("[SUCCESS] Schema initialized: data_raw, data_cleansed, sentiment_results.")

    except mysql.connector.Error as err:
        print(f"[ERROR] Database initialization failed: {err}")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    initialize_database()