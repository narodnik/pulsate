import asyncio
import binascii
import codecs
import iterfzf
from pulsate import cli
from pulsate import db

async def gather_contact_dict(config):
    contact_dict = {}

    signal = cli.SignalCli()
    await signal.connect()

    if config is None:
        database_filename = "pulsate.db"
    else:
        database_filename = config["database"]

    signal_db = db.SignalMessageDatabase(database_filename)
    for number in signal_db.fetch_numbers():
        name = await signal.get_contact_name(number)
        if not name:
            continue
        contact_dict[name] = number

    # Also add in groups too

    group_ids = await signal.get_group_ids()
    for group_id in group_ids:
        name = await signal.get_group_name(group_id)

        if not name:
            continue

        contact_dict[name] = codecs.encode(group_id, 'hex').decode('ascii')

    return contact_dict

def compute_contact_dict(config):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(gather_contact_dict(config))

def select_contact(choice=None, config=None):
    contact_dict = compute_contact_dict(config)

    if choice is None:
        number = iterfzf.iterfzf(contact_dict.keys())
        channel = contact_dict[number]
    else:
        choices = [name for name in contact_dict.keys()
                   if name.startswith(choice)]
        if len(choices) > 1:
            name = iterfzf.iterfzf(choices)
            channel = contact_dict[name]
        elif len(choices) == 1:
            name = choices[0]
            channel = contact_dict[name]
        else:
            channel = choice

    try:
        is_group = True
        channel = codecs.decode(channel, 'hex')
    except binascii.Error:
        is_group = False

    return channel, is_group

