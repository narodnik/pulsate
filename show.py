import asyncio
import codecs
import pulsate
import magic

async def main():
    signal = pulsate.SignalCli()
    await signal.connect()

    config = pulsate.load_config()
    database_filename = config["database"]
    signal_db = pulsate.SignalMessageDatabase(database_filename)

    my_telephone = config["my_telephone"]

    for message in signal_db.fetch()[-60:]:
        display_line = ""

        if message.group_id:
            group_name = await signal.get_group_name(message.group_id)
            if group_name == "":
                group_name = "(Unnamed group)"

            group_id = codecs.encode(message.group_id, 'hex').decode('ascii')
            group_name += " %s" % group_id
        else:
            group_name = None

        if message.destination is None:
            if group_name:
                display_line += "%s - " % group_name

            if message.source == my_telephone:
                contact_name = "Me"
            else:
                contact_name = await signal.get_contact_name(message.source)

            if contact_name is None:
                display_line += "%s: %s" % (message.source, message.text)
            else:
                display_line += "%s (%s): %s" % (
                    contact_name, message.source, message.text)
        else:
            destination = await signal.get_contact_name(message.destination)

            display_line += "Me to %s (%s): %s" % (
                destination, message.destination, message.text)

        print(display_line)

        if message.attachments:
            for attachment in message.attachments:
                print("  Attachment:", magic.from_file(attachment, mime=True),
                                       attachment)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

