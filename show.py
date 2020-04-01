import asyncio
import signalcli
import sqlite3

class SignalMessageDatabase:
    def __init__(self, filename):
        self._database = sqlite3.connect("main.db")
        self._cursor = self._database.cursor()

    def fetch(self):
        messages = []

        self._cursor.execute("""
            SELECT id, timestamp, source, destination, group_id, text
            FROM messages
            ORDER BY timestamp ASC
        """)

        for (message_id, timestamp, source, destination, group_id, text) \
            in self._cursor.fetchall():

            group_id = [x for x in group_id] if group_id is not None else None

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

import magic

async def main():
    my_telephone = "+34685646266"
    signal = signalcli.SignalCli(my_telephone)
    await signal.connect()

    signal_db = SignalMessageDatabase("main.db")

    for message in signal_db.fetch():
        display_line = ""

        if message.group_id:
            group_name = await signal.get_group_name(message.group_id)
            if group_name == "":
                group_name = "(Unnamed group)"
        else:
            group_name = None

        if message.destination is None:
            if group_name:
                display_line += "%s - " % group_name

            contact_name = await signal.get_contact_name(message.source)
            display_line += "%s: %s" % (contact_name, message.text)
        else:
            if group_name:
                destination = group_name
            else:
                destination = await signal.get_contact_name(message.destination)

            display_line += "Me to %s: %s" % (destination, message.text)

        print(display_line)

        if message.attachments:
            for attachment in message.attachments:
                print("  Attachment:", magic.from_file(attachment, mime=True),
                                       attachment)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

