import asyncio
import dbus_next.aio as dbus
import janus
import sys

signal_bus_name = "org.asamk.Signal"
signal_path_name = "/org/asamk/Signal"
signal_iface_name = "org.asamk.Signal"

class SignalMessage:

    def __init__(self, timestamp, source, destination, group_id,
                 text, attachments):
        self.timestamp = timestamp
        self.source = source
        self.destination = destination
        self.group_id = group_id if group_id else None
        self.text = text
        self.attachments = attachments

class SignalCli:

    def __init__(self):
        self._interface = None

    async def connect(self):
        bus = await dbus.MessageBus().connect()

        introspection = await bus.introspect(signal_bus_name,
                                             signal_path_name)

        proxy_object = bus.get_proxy_object(signal_bus_name,
                                            signal_path_name,
                                            introspection)

        self._interface = proxy_object.get_interface(signal_iface_name)
        self._interface.on_message_received(self._on_message_received)
        self._interface.on_sync_message_received(self._on_sync_message_received)

        self._queue = janus.Queue(loop=asyncio.get_event_loop())

    def _on_message_received(self, timestamp, sender,
                             group_id, message, attachments):
        message = SignalMessage(timestamp, sender, None,
                                group_id, message, attachments)
        self._queue.sync_q.put(message)

    def _on_sync_message_received(self, timestamp, source, destination,
                                  group_id, message, attachments):
        message = SignalMessage(timestamp, source, destination,
                                group_id, message, attachments)
        self._queue.sync_q.put(message)

    def handle_message(self, connection, message, user_data) :
        if message.member == "MessageReceived":
            # timestamp, number, [group id], message, [attachments]
            objects = message.expect_objects("xsaysas")
            timestamp, source, group_id, message, attachments = objects
            message = SignalMessage(timestamp, source, None, group_id,
                                    message, attachments)
        elif message.member == "SyncMessageReceived":
            # timestamp, source, dest, [group id], message, [attachments]
            objects = message.expect_objects("xssaysas")
            message = SignalMessage(*objects)
        else:
            print("Internal error: unhandled member type", file=sys.stderr)
        self._queue.sync_q.put(message)
        return DBUS.HANDLER_RESULT_HANDLED

    async def receive_message(self):
        return await self._queue.async_q.get()

    async def group_members(self, group_id):
        numbers = await self._interface.call_get_group_members(group_id)
        return numbers

    async def get_contact_name(self, number):
        name = await self._interface.call_get_contact_name(number)
        return name

    async def get_group_ids(self):
        group_ids = await self._interface.call_get_group_ids()
        return group_ids

    async def get_group_name(self, group_id):
        name = await self._interface.call_get_group_name(group_id)
        return name

    async def send_message(self, message, attachments, recipient):
        await self._interface.call_send_message(message, attachments, recipient)

    async def send_group_message(self, message, attachments, group_id):
        await self._interface.call_send_group_message(
            message, attachments, group_id)

async def main():
    import codecs

    my_telephone = "+34685646266"

    signal = SignalCli()
    await signal.connect()

    group_ids = await signal.get_group_ids()
    for group_id in group_ids:
        name = await signal.get_group_name(group_id)
        print(codecs.encode(group_id, 'hex'), name)

        numbers = await signal.group_members(group_id)
        for number in numbers:
            if number == my_telephone:
                continue
            name = await signal.get_contact_name(number)
            print("    %s\t%s" % (name, number))

    #while True:
    #    message = await signal.receive_message()
    #    print(message, message.text)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

