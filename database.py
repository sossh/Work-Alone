from abc import ABC, abstractmethod
import sqlite3
import time
from venv import logger


import psycopg2
import psycopg2.extras


#
# Handles low level database operations like executing queries and writes
#


# Interface for Database operations
class Database(ABC):
    
    @abstractmethod
    def execute_query(self, sql: str, params:list) -> list[dict]:
        ''' Executes a read-only query and returns the results as a list of dictionaries. '''
        pass

    @abstractmethod
    def execute_write(self, sql: str, params:list) -> int:
        ''' Executes a write query (INSERT, UPDATE, DELETE) and returns the number of affected rows. '''
        pass

    @abstractmethod
    def close(self) -> None:
        ''' Closes the database connection. '''
        pass


# SQLite implementation of the Database interface
class SqliteDatabase(Database):

    def __init__(self, db_path: str):
        
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row  # returns dict-like rows
        self.connection.execute("PRAGMA journal_mode=WAL;")
        self.connection.commit()
        self.cursor = self.connection.cursor()

        self.max_retries = 5
        self.retry_delay = 0.1  # seconds

    def execute_query(self, sql: str, params:list=[]) -> list[dict]:
        self.cursor.execute(sql, params)
        rows = []
        for row in self.cursor.fetchall():
            rows.append(dict(row))
        
        return rows
    
    def execute_write(self, sql: str, params:list=[]) -> int:
        
        attempt = 0
        while attempt < self.max_retries:
            try:
                self.cursor.execute(sql, params)
                self.connection.commit()
                break

            # Check for database lock error and retry
            except sqlite3.OperationalError as e:
                attempt += 1
                if "database is locked" in str(e):
                    time.sleep(self.retry_delay)  # wait before retry
        
        # Return the number of affected rows
        affected = self.cursor.rowcount
        if affected == -1 or affected is None:
            return 0
        return affected
    
    def close(self) -> None:
        try:
            self.cursor.close()
        finally:
            self.connection.close()




class PostgresDatabase(Database):
    
    def __init__(self, host: str, dbname: str, user: str, password: str, port: int = 5432):
        if not all([host, dbname, user, password]):
            raise ValueError("All database connection parameters are required")
        
        try:
            self.connection = psycopg2.connect(
                host=host,
                dbname=dbname,
                user=user,
                password=password,
                port=port,
                connect_timeout=5
            )
            self.connection.autocommit = True
            self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            print(f"PostgreSQL database connection established: {user}@{host}:{port}/{dbname}")
        except psycopg2.OperationalError as e:
            print(f"Failed to connect to PostgreSQL database: {e}")
            raise
        except psycopg2.Error as e:
            print(f"PostgreSQL error during initialization: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error initializing PostgreSQL database: {e}")
            raise

    def execute_query(self, sql: str, params: list = []) -> list[dict]:
        if not sql or not sql.strip():
            print("execute_query called with empty SQL")
            return []
        
        # Make sure this is a read-only query
        if not sql.strip().lower().startswith("select") and not sql.strip().lower().startswith("with"):
            print(f"execute_query called with non-SELECT statement: {sql[:50]}...")
            return []
        
        try:
            self.cursor.execute(sql, params)
            results = self.cursor.fetchall()
            return results
        
        except psycopg2.Error as e:
            print(f"PostgreSQL query error: {e}\nSQL: {sql}\nParams: {params}")
            return []
        except Exception as e:
            print(f"Unexpected error executing query: {e}")
            return []

    def execute_write(self, sql: str, params: list = []) -> int:
        if not sql or not sql.strip():
            print("execute_write called with empty SQL")
            return 0
        
        try:
            self.cursor.execute(sql, params)
            affected = self.cursor.rowcount
            
            if affected == -1 or affected is None:
                affected = 0
            
            return affected
        
        except psycopg2.IntegrityError as e:
            print(f"Integrity constraint violation: {e}\nSQL: {sql}\nParams: {params}")
            return 0
        
        except psycopg2.OperationalError as e:
            print(f"PostgreSQL operational error (connection issue): {e}")
            return 0
        
        except psycopg2.Error as e:
            print(f"PostgreSQL write error: {e}\nSQL: {sql}\nParams: {params}")
            return 0
        
        except Exception as e:
            print(f"Unexpected error during write operation: {e}")
            return 0

    def close(self) -> None:
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            print("PostgreSQL connection closed successfully")
        except psycopg2.Error as e:
            print(f"Error closing PostgreSQL connection: {e}")
        except Exception as e:
            print(f"Unexpected error closing connection: {e}")