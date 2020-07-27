#!/usr/bin/python
import argparse
import asyncio
import codecs
import pulsate
import sys
import magic

async def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('--filter')
    parser.add_argument('--total', type=int)
    args = parser.parse_args()

    total = args.total if args.total is not None else 40

    signal = pulsate.SignalCli()
    await signal.connect()

    config = pulsate.load_config()
    database_filename = config["database"]
    signal_db = pulsate.SignalMessageDatabase(database_filename)

    my_telephone = config["my_telephone"]

    for message in signal_db.fetch()[-total:]:
        display_prefix = ""

        if message.group_id:
            group_name = await signal.get_group_name(message.group_id)
            if group_name is None:
                group_name = "(Unnamed group)"

            if args.filter is not None and group_name != args.filter:
                continue

            group_id = codecs.encode(message.group_id, 'hex').decode('ascii')
            group_name += " %s" % group_id
        else:
            group_name = None

        if message.destination is None:
            if group_name:
                display_prefix += "%s - " % group_name

            if message.source == my_telephone:
                contact_name = "Me"
            else:
                contact_name = await signal.get_contact_name(message.source)

            if args.filter is not None and contact_name != args.filter:
                continue

            if contact_name is None:
                display_prefix += "%s" % message.source
            else:
                display_prefix += "%s (%s)" % (
                    contact_name, message.source)
        else:
            destination = await signal.get_contact_name(message.destination)

            if args.filter is not None and destination != args.filter:
                continue

            display_prefix += "Me to %s (%s)" % (
                destination, message.destination)

        if message.text:
            print("%s: %s" % (display_prefix, message.text))

        for attachment in message.attachments:
            try:
                file_type = magic.from_file(attachment, mime=True)
            except FileNotFoundError:
                file_type = "<deleted>"

            print("%s: Attachment: %s %s" %
                  (display_prefix, file_type, attachment))

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main(sys.argv))

