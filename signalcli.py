import asyncio
import janus
import dbussy as dbus
import sys
from dbussy import DBUS

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

    def __init__(self, telephone):
        self._telephone = telephone
        self._connection = None

    async def connect(self):
        loop = asyncio.get_event_loop()

        self._connection = await dbus.Connection.bus_get_async(
            type=DBUS.BUS_SESSION,
            private=False,
            loop=loop
        )

        self._connection.bus_add_match({
            "type": "signal",
            "interface": signal_iface_name,
            "member": "MessageReceived"
        })
        self._connection.bus_add_match({
            "type": "signal",
            "interface": signal_iface_name,
            "member": "SyncMessageReceived"
        })
        self._connection.register_fallback(
            path=signal_path_name,
            vtable=dbus.ObjectPathVTable(
                loop=loop,
                message=self.handle_message
            ),
            user_data=None
        )

        self._queue = janus.Queue(loop=loop)

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

    async def _make_request(self, method, arg_string, *args):
        assert self._connection is not None
        message = dbus.Message.new_method_call(
            destination=signal_bus_name,
            path=signal_path_name,
            iface=signal_iface_name,
            method=method
        )
        message.append_objects(arg_string, *args)
        reply = await self._connection.send_await_reply(message)
        return reply

    async def group_members(self, group_id):
        reply = await self._make_request("getGroupMembers", "ay", group_id)
        numbers = reply.expect_return_objects("as")[0]
        return numbers

    async def get_contact_name(self, number):
        reply = await self._make_request("getContactName", "s", number)
        name = reply.expect_return_objects("s")[0]
        return name

    async def get_group_ids(self):
        reply = await self._make_request("getGroupIds", "")
        group_ids = reply.expect_return_objects("aay")[0]
        return group_ids

    async def get_group_name(self, group_id):
        reply = await self._make_request("getGroupName", "ay", group_id)
        name = reply.expect_return_objects("s")[0]
        return name

async def main():
    my_telephone = "+34685646266"
    signal = SignalCli(my_telephone)
    await signal.connect()

    group_id = [0xdc,0x69,0x2f,0x97,0x0e,0xc8,0x20,0x42,0xdb,0xa9,0x8b,0xe1,0xbf,0x6e,0xf1,0x18]
    numbers = await signal.group_members(group_id)
    #print(numbers)

    for number in numbers:
        if number == my_telephone:
            continue
        name = await signal.get_contact_name(number)
        print("%s (%s)" % (name, number))

    print("==== GROUPS ====")
    group_ids = await signal.get_group_ids()
    for group_id in group_ids:
        name = await signal.get_group_name(group_id)
        print(name)

    while True:
        message = await signal.receive_message()
        print(message)

    #reply = await make_request("sendGroupMessage", "sasay", "sending new message", [], group_id)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

