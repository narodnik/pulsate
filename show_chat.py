import asyncio
import magic
import pulsate
import sys

class ShowOff:

    def __init__(self, config, channel, is_group):
        self.config = config
        self.channel = channel
        self.is_group = is_group
        self.my_telephone = config["my_telephone"]
        self.contact_names = {}

        if self.is_group:
            assert isinstance(self.channel, bytes)
        else:
            assert isinstance(self.channel, str)

    async def main(self):
        self.signal = pulsate.SignalCli()
        await self.signal.connect()

        database_filename = self.config["database"]
        self.signal_db = pulsate.SignalMessageDatabase(database_filename)

        for message in self.signal_db.fetch():
            await self.update(message)

    async def update(self, message):
        if self.is_group:
            if message.group_id == self.channel:
                await self.update_group(message)
        else:
            if (message.source == self.my_telephone
                    and message.destination == self.channel):
                self.update_sent(message)
            elif message.source == self.channel and message.group_id is None:
                await self.update_receive(message)

    async def update_group(self, message):
        assert self.is_group and message.group_id == self.channel

        if message.source == self.my_telephone:
            self.update_sent(message)
        else:
            await self.update_receive(message)

    async def update_receive(self, message):
        assert ((self.is_group and message.group_id == self.channel
                and message.source != self.my_telephone)
            or (not self.is_group and message.source != self.my_telephone
                and message.destination is None))

        number = message.source
        if number not in self.contact_names:
            self.contact_names[number] = \
                await self.signal.get_contact_name(number)

        contact_name = self.contact_names[number]

        if message.text:
            self.print_message(contact_name, message.text)

        self.update_attachments(contact_name, message.attachments)

    def update_sent(self, message):
        assert (message.source == self.my_telephone
            and ((self.is_group and message.group_id == self.channel)
                 or (not self.is_group
                     and message.destination == self.channel)))

        if message.text:
            self.print_message("", message.text)

        self.update_attachments("", message.attachments)

    def update_attachments(self, contact_name, attachments):
        for attachment in attachments:
            try:
                file_type = magic.from_file(attachment, mime=True)
            except OSError:
                file_type = "<deleted>"

            self.print_message(contact_name, "[Attachment: %s %s]" % (
                file_type, attachment))

    def print_sent_message(self, text):
        print("> %s" % text)
 
    def print_message(self, contact_name, text):
        text = "> %s" % text

        if contact_name:
            text = contact_name + text

        print(text)

async def amain(config, channel, is_group):
    showoff = ShowOff(config, channel, is_group)
    await showoff.main()

def main(argv):
    config = pulsate.load_config()

    if len(argv) == 2:
        choice = sys.argv[1]
    else:
        choice = None

    channel, is_group = pulsate.select_contact(choice, config)

    asyncio.run(amain(config, channel, is_group))

if __name__ == "__main__":
    main(sys.argv)

