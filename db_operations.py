import sqlite3, queue

# --- Database Configuration ---
DB_FILE = 'conversation_history.db'
task_queue = queue.Queue()

def create_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            ip_address TEXT,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (conversation_id)
        )
    ''')
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect(DB_FILE, timeout=300)

def insert_message(conversation_id, ip_address, role, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (conversation_id, ip_address, role, content) VALUES (?, ?, ?, ?)",
        (conversation_id, ip_address, role, content)
    )
    conn.commit()
    conn.close()

def create_conversation(thread_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO conversations (thread_id) VALUES (?)", (thread_id,))
    conversation_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return conversation_id

def database_worker():
    while True:
        item = task_queue.get()
        if item is None:
            break
        # Unpack the task: (function, *args)
        func, *args = item
        try:
            func(*args)
        except Exception as e:
            print(f"Error processing task: {e}")
        finally:
            task_queue.task_done()