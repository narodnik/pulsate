import argparse
import sys

import pulsate

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--user')
    args = parser.parse_args()

    if args.user is None:
        return -1

    choice = args.user

    config = pulsate.load_config()
    channel, is_group = pulsate.select_contact(choice, config)

    if is_group:
        print("error: no support for groups yet", file=sys.stderr)
        return -1

    database_filename = config["database"]
    signal_db = pulsate.SignalMessageDatabase(database_filename)

    for message in signal_db.fetch_by_source(channel):
        print(message.text)

if __name__ == "__main__":
    sys.exit(main())
