import signalcli
import sqlite3

class SignalMessageDatabase:
    def __init__(self, filename="main.db"):
        self._database = sqlite3.connect(filename)
        self._cursor = self._database.cursor()

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
            message = signalcli.SignalMessage(timestamp, source, destination,
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
        return self._cursor.fetchall()

