import os
import psycopg2
from psycopg2 import pool
from threading import Lock
from dotenv import load_dotenv
import os


env_path = os.path.join(os.path.dirname(__file__), '.env')  # current folder
load_dotenv(env_path)

# Optional: check if variables are loaded
print("DB_NAME:", os.getenv("DB_NAME"))
print("DB_USER:", os.getenv("DB_USER"))
print("DB_PASSWORD:", os.getenv("DB_PASSWORD"))
print("DB_HOST:", os.getenv("DB_HOST"))


class DatabaseConnection:
    """
    Singleton class for managing PostgreSQL connections using connection pooling.
    """

    _instance = None
    _lock = Lock()  # ensures thread safety when instantiating

    def __new__(cls, *args, **kwargs):
        # Implement the Singleton pattern
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance

    def __init__(self,
                 dbname=None,
                 user=None,
                 password=None,
                 host=None,
                 port=5432,
                 minconn=1,
                 maxconn=5):
        """
        Initialize the database connection pool if it doesn't already exist.
        """
        # If explicit values weren't provided, read from environment variables.
        dbname = dbname or os.getenv('DB_NAME') or os.getenv('DB_DATABASE')
        user = user or os.getenv('DB_USER')
        password = password or os.getenv('DB_PASSWORD')
        host = host or os.getenv('DB_HOST')
        port = port or int(os.getenv('DB_PORT') or 5432)
        minconn = minconn or int(os.getenv('DB_MINCONN') or 1)
        maxconn = maxconn or int(os.getenv('DB_MAXCONN') or 5)

        if not hasattr(self, "_pool"):  # avoid re-initialization
            try:
                if not all([dbname, user, password, host]):
                    raise ValueError("Database configuration incomplete. Please set DB_NAME, DB_USER, DB_PASSWORD and DB_HOST in environment or pass them to DatabaseConnection.")

                self._pool = psycopg2.pool.SimpleConnectionPool(
                    minconn=minconn,
                    maxconn=maxconn,
                    dbname=dbname,
                    user=user,
                    password=password,
                    host=host,
                    port=port
                )
                print("Connection pool created successfully.")
            except Exception as e:
                print(f"Error creating connection pool: {e}")
                self._pool = None

    def get_connection(self):
        """Retrieve a connection from the pool."""
        if not self._pool:
            raise Exception("Connection pool not initialized.")
        return self._pool.getconn()

    def release_connection(self, connection):
        """Return a connection back to the pool."""
        if self._pool:
            self._pool.putconn(connection)

    def close_all_connections(self):
        """Close all database connections."""
        if self._pool:
            self._pool.closeall()
            print("All database connections closed.")


# Example usage
if __name__ == "__main__":
    # Example: create DatabaseConnection using environment variables.
    db = DatabaseConnection()

    conn = db.get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT version();")
        print("PostgreSQL version:", cur.fetchone())
    finally:
        db.release_connection(conn)
        db.close_all_connections()
