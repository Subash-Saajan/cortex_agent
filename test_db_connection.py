import sys
import psycopg2

def test_connection(password):
    host = "cortex-agent-db.cafuw86ac9wv.us-east-1.rds.amazonaws.com"
    port = "5432"
    database = "cortexdb"
    user = "postgres"
    
    print(f"Attempting to connect to {host}:{port}/{database} as {user}...")
    
    try:
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port,
            connect_timeout=5
        )
        print("✅ SUCCESS: Connection successful!")
        conn.close()
        return True
    except psycopg2.OperationalError as e:
        print(f"❌ CONNECTION FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_db_connection.py <your_password>")
        sys.exit(1)
    
    password = sys.argv[1]
    test_connection(password)
