import asyncio
import signalcli
import sqlite3

async def main():
    signal = signalcli.SignalCli()
    await signal.connect()

    database = sqlite3.connect("main.db")
    cursor = database.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY,
            timestamp INTEGER NOT NULL,
            source TEXT NOT NULL,
            destination TEXT,
            group_id BLOB,
            text TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attachments(
            id INTEGER PRIMARY KEY,
            message_id INTEGER NOT NULL,
            attachment TEXT NOT NULL
        )
    """)

    database.commit()

    while True:
        message = await signal.receive_message()

        cursor.execute("""
            INSERT INTO messages (timestamp, source, destination,
                                  group_id, text)
            VALUES (?, ?, ?, ?, ?)
        """, (message.timestamp, message.source, message.destination,
              group_id, message.text))

        message_id = cursor.lastrowid

        for attachment in message.attachments:
            cursor.execute("""
                INSERT INTO attachments (message_id, attachment)
                VALUES (?, ?)
            """, (message_id, attachment))

        database.commit()

        # Display the info

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
                print("  Attachment:", attachment)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

