import sqlite3

def init_db():
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            input TEXT NOT NULL,
            response TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS unanswered (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT,
            bot_response TEXT,
            response_id INTEGER,
            rating INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (response_id) REFERENCES responses(id)
        )
    """)

    conn.commit()
    conn.close()


def log_chat(user_message, bot_response, response_id=None):
    """Log a chat interaction to the chat_logs table."""
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO chat_logs (user_message, bot_response, response_id)
        VALUES (?, ?, ?)
    """, (user_message, bot_response, response_id))
    
    conn.commit()
    log_id = cursor.lastrowid
    conn.close()
    
    return log_id


def rate_chat_log(log_id, rating):
    """Update rating for a chat log entry."""
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE chat_logs
        SET rating = ?
        WHERE id = ?
    """, (rating, log_id))
    
    conn.commit()
    conn.close()


def get_chat_stats():
    """Get statistics for all chat logs."""
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_chats,
            AVG(rating) as avg_rating,
            SUM(CASE WHEN rating IS NOT NULL THEN 1 ELSE 0 END) as rated_count
        FROM chat_logs
    """)
    
    stats = cursor.fetchone()
    conn.close()
    
    return {
        "total_chats": stats[0],
        "avg_rating": stats[1],
        "rated_count": stats[2]
    }


def insert_sample_data():
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()

    data = [
        ("hello hi hey", "Hi there!"),
        ("bye goodbye", "Goodbye!"),
        ("tables table stands price cost", "Table stands go for as low as 10,000 to 20,000!"),
        ("chairs chair price cost", "Chairs are going for 5,000 to 10,000 depending on the quality."),
        ("discounts discount sale promo promotion", "Yes, we have a 10% discount for bulk purchases."),
        ("colors color available", "Sure! We have black, white, and brown for the table stands, and the chairs come in black, white, and red."),
        ("return policy returns refund", "We offer a 30-day return policy for any defective products. Please keep the receipt for returns."),
        ("delivery deliver shipping", "Yes, we offer delivery services for an additional fee based on your location. Please provide your address for a quote."),
        ("customize customization design", "Yes, we offer customization options for the table stands. You can choose the size, color, and material."),
        ("payment pay methods options", "We accept cash, credit/debit cards, and mobile payments."),
        ("warranty guarantee", "Yes, we offer a 1-year warranty on all our products."),
        ("quote bulk order purchase", "Please provide the quantity and specifications for a quote."),
        ("buy purchase order", "Great! Would you like pricing or customization details?")
    ]

    cursor.executemany(
        "INSERT INTO responses (input, response) VALUES (?, ?)",
        data
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    insert_sample_data()
    print("Database created and sample data inserted successfully!")