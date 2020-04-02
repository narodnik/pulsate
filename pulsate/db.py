import sqlite3
from pulsate import cli

class SignalMessageDatabase:
    def __init__(self, filename="main.db"):
        self._database = sqlite3.connect(filename)
        self._cursor = self._database.cursor()
        self._initialize()

    def _initialize(self):
        self._cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY,
                timestamp INTEGER NOT NULL,
                source TEXT NOT NULL,
                destination TEXT,
                group_id BLOB,
                text TEXT NOT NULL
            )
        """)

        self._cursor.execute("""
            CREATE TABLE IF NOT EXISTS attachments(
                id INTEGER PRIMARY KEY,
                message_id INTEGER NOT NULL,
                attachment TEXT NOT NULL
            )
        """)

        self._database.commit()

    def fetch(self, begin_timestamp=0):
        messages = []

        self._cursor.execute("""
            SELECT id, timestamp, source, destination, group_id, text
            FROM messages
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (begin_timestamp,))

        for (message_id, timestamp, source, destination, group_id, text) \
            in self._cursor.fetchall():

            self._cursor.execute("""
                SELECT attachment
                FROM attachments
                WHERE message_id=?
            """, (message_id,))
            attachments = [attachment for (attachment,)
                           in self._cursor.fetchall()]
            message = cli.SignalMessage(timestamp, source, destination,
                                              group_id, text, attachments)
            messages.append(message)

        return messages

    def fetch_numbers(self):
        self._cursor.execute("""
            SELECT source
            FROM messages
            UNION
            SELECT destination
            FROM messages
            WHERE destination IS NOT NULL
        """)
        return [number for (number,) in self._cursor.fetchall()
                if number is not None]

    def add(self, message):
        self._cursor.execute("""
            INSERT INTO messages (timestamp, source, destination,
                                  group_id, text)
            VALUES (?, ?, ?, ?, ?)
        """, (message.timestamp, message.source, message.destination,
              message.group_id, message.text))

        message_id = self._cursor.lastrowid

        for attachment in message.attachments:
            self._cursor.execute("""
                INSERT INTO attachments (message_id, attachment)
                VALUES (?, ?)
            """, (message_id, attachment))

        self._database.commit()

