import asyncio
import dbus_next.aio as dbus
import dbus_next
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

    def __repr__(self):
        return ("<timestamp=%s source=%s destination=%s group_id=%s "
            + "text=%s attachments=%s>") % (
                self.timestamp, self.source, self.destination, self.group_id,
                self.text, self.attachments
            )

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

        self._queue = janus.Queue()

    def _on_message_received(self, timestamp, sender,
                             group_id, message, attachments):
        if not message and not attachments:
            return
        message = SignalMessage(timestamp, sender, None,
                                group_id, message, attachments)
        self._queue.sync_q.put(message)

    def _on_sync_message_received(self, timestamp, source, destination,
                                  group_id, message, attachments):
        if not message and not attachments:
            return
        destination = destination if destination else None
        message = SignalMessage(timestamp, source, destination,
                                group_id, message, attachments)
        self._queue.sync_q.put(message)

    async def receive_message(self):
        return await self._queue.async_q.get()

    async def group_members(self, group_id):
        numbers = await self._interface.call_get_group_members(group_id)
        return numbers

    async def get_contact_name(self, number):
        try:
            name = await self._interface.call_get_contact_name(number)
            return name
        except dbus_next.errors.DBusError:
            return None

    async def get_group_ids(self):
        group_ids = await self._interface.call_get_group_ids()
        return group_ids

    async def get_group_name(self, group_id):
        try:
            return await self._interface.call_get_group_name(group_id)
        except dbus_next.errors.DBusError:
            return None

    async def send_message(self, message, attachments, recipient):
        timestamp = await self._interface.call_send_message(
            message, attachments, recipient)
        return timestamp

    async def send_group_message(self, message, attachments, group_id):
        timestamp = await self._interface.call_send_group_message(
            message, attachments, group_id)
        return timestamp

async def main():
    import codecs
    from pulsate.config import load_config

    config = pulsate.load_config()
    my_telephone = config["my_telephone"]

    signal = SignalCli()
    await signal.connect()

    group_ids = await signal.get_group_ids()
    for group_id in group_ids:
        name = await signal.get_group_name(group_id)
        print(codecs.encode(group_id, 'hex').decode('ascii'), name)

        numbers = await signal.group_members(group_id)
        for number in numbers:
            if number == my_telephone:
                continue
            name = await signal.get_contact_name(number)
            print("    %s\t%s" % (name, number))

    while True:
        message = await signal.receive_message()
        print(message, message.text)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

