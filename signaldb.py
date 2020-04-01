import signalcli
import sqlite3

class SignalMessageDatabase:
    def __init__(self, filename):
        self._database = sqlite3.connect("main.db")
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

