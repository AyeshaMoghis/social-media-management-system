import os

import mysql.connector

# Connect to database
conn = mysql.connector.connect(
    host=os.getenv('MYSQL_HOST', '127.0.0.1'),
    user=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD', ''),
    database=os.getenv('MYSQL_DB', 'smms')
)

cursor = conn.cursor()

try:
    # Update scheduled_post status ENUM
    print("Updating scheduled_post table...")
    cursor.execute("""
        ALTER TABLE scheduled_post 
        MODIFY COLUMN status ENUM('pending', 'scheduled', 'published', 'failed') 
        DEFAULT 'scheduled'
    """)
    conn.commit()
    print("✅ Database schema updated successfully!")
    
    # Verify the change
    cursor.execute("DESCRIBE scheduled_post")
    print("\nUpdated scheduled_post structure:")
    for row in cursor.fetchall():
        print(row)
        
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()
