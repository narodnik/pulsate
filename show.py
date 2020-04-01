import asyncio
import codecs
import signalcli
import signaldb
import magic

async def main():
    signal = signalcli.SignalCli()
    await signal.connect()

    signal_db = signaldb.SignalMessageDatabase("main.db")

    for message in signal_db.fetch()[-40:]:
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

