#!/usr/bin/python
import asyncio
import dbus_next
import subprocess
import pulsate
import sqlite3

async def main():
    config = pulsate.load_config()
    my_telephone = config["my_telephone"]

    cmd = 'signal-cli -u "%s" daemon' % my_telephone
    process = subprocess.Popen(cmd, shell=True)

    signal = pulsate.SignalCli()

    # Keep trying connect until it works
    while True:
        try:
            await signal.connect()
            break
        except dbus_next.errors.DBusError:
            continue

    config = pulsate.load_config()
    database_filename = config["database"]
    signal_db = pulsate.SignalMessageDatabase(database_filename)

    while True:
        message = await signal.receive_message()
        signal_db.add(message)

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

