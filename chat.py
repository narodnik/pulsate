#!/usr/bin/python
# coding: UTF-8

# code extracted from nigiri

import asyncio
import os
import datetime
import magic
import sys
import traceback
import re
import time
import logging
import locale
#import commands

import urwid
from urwid import MetaSignals

import pulsate

class ExtendedListBox(urwid.ListBox):
    """
        Listbow widget with embeded autoscroll
    """

    __metaclass__ = urwid.MetaSignals
    signals = ["set_auto_scroll"]


    def set_auto_scroll(self, switch):
        if type(switch) != bool:
            return
        self._auto_scroll = switch
        urwid.emit_signal(self, "set_auto_scroll", switch)


    auto_scroll = property(lambda s: s._auto_scroll, set_auto_scroll)


    def __init__(self, body):
        urwid.ListBox.__init__(self, body)
        self.auto_scroll = True


    def switch_body(self, body):
        if self.body:
            urwid.disconnect_signal(body, "modified", self._invalidate)

        self.body = body
        self._invalidate()

        urwid.connect_signal(body, "modified", self._invalidate)


    def keypress(self, size, key):
        urwid.ListBox.keypress(self, size, key)

        if key in ("page up", "page down"):
            logging.debug("focus = %d, len = %d" % (self.get_focus()[1], len(self.body)))
            if self.get_focus()[1] == len(self.body)-1:
                self.auto_scroll = True
            else:
                self.auto_scroll = False
            logging.debug("auto_scroll = %s" % (self.auto_scroll))


    def scroll_to_bottom(self):
        logging.debug("current_focus = %s, len(self.body) = %d" % (self.get_focus()[1], len(self.body)))

        if self.auto_scroll:
            # at bottom -> scroll down
            self.set_focus(len(self.body) - 1)



"""
 -------context-------
| --inner context---- |
|| HEADER            ||
||                   ||
|| BODY              ||
||                   ||
|| DIVIDER           ||
| ------------------- |
| FOOTER              |
 ---------------------

inner context = context.body
context.body.body = BODY
context.body.header = HEADER
context.body.footer = DIVIDER
context.footer = FOOTER

HEADER = Notice line (urwid.Text)
BODY = Extended ListBox
DIVIDER = Divider with information (urwid.Text)
FOOTER = Input line (Ext. Edit)
"""


class MainWindow(object):

    __metaclass__ = MetaSignals
    signals = ["quit","keypress"]

    _palette = [
            ('divider','black','dark cyan', 'standout'),
            ('text','light gray', 'default'),
            ('bold_text', 'light gray', 'default', 'bold'),
            ("body", "text"),
            ("footer", "text"),
            ("header", "text"),
        ]

    for type, bg in (
            ("div_fg_", "dark cyan"),
            ("", "default")):
        for name, color in (
                ("red","dark red"),
                ("blue", "dark blue"),
                ("green", "dark green"),
                ("yellow", "yellow"),
                ("magenta", "dark magenta"),
                ("gray", "light gray"),
                ("white", "white"),
                ("black", "black")):
            _palette.append((type + name, color, bg))

    def __init__(self, config, channel, is_group):
        self.config = config
        self.shall_quit = False

        self.channel = channel
        self.is_group = is_group
        self.my_telephone = config["my_telephone"]
        self.contact_names = {}

        if self.is_group:
            assert isinstance(self.channel, bytes)
        else:
            assert isinstance(self.channel, str)

    def main(self):
        """ 
            Entry point to start UI 
        """

        self.ui = urwid.raw_display.Screen()
        self.ui.register_palette(self._palette)
        self.build_interface()

        with self.ui.start():
            self.run()

    async def sync(self):
        self.signal = pulsate.SignalCli()
        await self.signal.connect()

        database_filename = self.config["database"]
        self.signal_db = pulsate.SignalMessageDatabase(database_filename)

        for message in self.signal_db.fetch():
            await self.update(message)

    async def receive(self):
        await self.sync()

        while True:
            message = await self.signal.receive_message()
            await self.update(message)

    async def send_message(self, text, attachments):
        if self.is_group:
            timestamp = await self.signal.send_group_message(
                text, attachments, self.channel)
        else:
            timestamp = await self.signal.send_message(
                text, attachments, [self.channel])

        message = pulsate.SignalMessage(
            timestamp,
            self.my_telephone,
            self.channel if not self.is_group else None,
            self.channel if self.is_group else None,
            text,
            attachments
        )
        self.signal_db.add(message)

        if text:
            self.print_sent_message(text)
        self.update_attachments("", attachments)

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
            except FileNotFoundError:
                file_type = "<deleted>"

            self.print_message(contact_name, "[Attachment: %s %s]" % (
                file_type, attachment))

    def run(self):
        """ 
            Setup input handler, invalidate handler to
            automatically redraw the interface if needed.

            Start mainloop.
        """

        # I don't know what the callbacks are for yet,
        # it's a code taken from the nigiri project
        def input_cb(key):
            if self.shall_quit:
                raise urwid.ExitMainLoop
            self.keypress(self.size, key)

        self.size = self.ui.get_cols_rows()

        loop = asyncio.get_event_loop()
        loop.create_task(self.receive())
        self.main_loop = urwid.MainLoop(
                self.context,
                screen=self.ui,
                handle_mouse=False,
                unhandled_input=input_cb,
                event_loop=urwid.AsyncioEventLoop(loop=loop),
            )

        def call_redraw(*x):
            self.draw_interface()
            invalidate.locked = False
            return True

        inv = urwid.canvas.CanvasCache.invalidate

        def invalidate (cls, *a, **k):
            inv(*a, **k)

            if not invalidate.locked:
                invalidate.locked = True
                self.main_loop.set_alarm_in(0, call_redraw)

        invalidate.locked = False
        urwid.canvas.CanvasCache.invalidate = classmethod(invalidate)

        try:
            self.main_loop.run()
        except KeyboardInterrupt:
            self.quit()


    def quit(self, exit=True):
        """ 
            Stops the ui, exits the application (if exit=True)
        """
        urwid.emit_signal(self, "quit")

        self.shall_quit = True

        if exit:
            sys.exit(0)


    def build_interface(self):
        """ 
            Call the widget methods to build the UI 
        """

        self.header = urwid.Text("Chat")
        self.footer = urwid.Edit("> ")
        self.divider = urwid.Text("Initializing.")

        self.generic_output_walker = urwid.SimpleListWalker([])
        self.body = ExtendedListBox(
            self.generic_output_walker)


        self.header = urwid.AttrWrap(self.header, "divider")
        self.footer = urwid.AttrWrap(self.footer, "footer")
        self.divider = urwid.AttrWrap(self.divider, "divider")
        self.body = urwid.AttrWrap(self.body, "body")

        self.footer.set_wrap_mode("space")

        main_frame = urwid.Frame(self.body, 
                                header=self.header,
                                footer=self.divider)
        
        self.context = urwid.Frame(main_frame, footer=self.footer)

        self.divider.set_text(("divider",
                               ("Send message:")))

        self.context.set_focus("footer")


    def draw_interface(self):
        self.main_loop.draw_screen()


    def keypress(self, size, key):
        """ 
            Handle user inputs
        """

        urwid.emit_signal(self, "keypress", size, key)

        # scroll the top panel
        if key in ("page up","page down"):
            self.body.keypress (size, key)

        # resize the main windows
        elif key == "window resize":
            self.size = self.ui.get_cols_rows()

        elif key in ("ctrl d", 'ctrl c'):
            self.quit()

        elif key in ("ctrl w"):
            while True:
                text = self.footer.edit_text
                self.footer.keypress((len(text),), "backspace")

                text = self.footer.edit_text
                pos = self.footer.edit_pos

                if not text or not pos or text[pos - 1] == " ":
                    break

        #elif key in ("ctrl left"):
        #    text = self.footer.edit_text
        #    pos = self.footer.edit_pos
        #    while True:
        #        self.footer.keypress((len(text),), "left")
        #        pos -= 1
        #        if text[pos - 1] == " ":
        #            break

        #elif key in ("ctrl right"):
        #    text = self.footer.edit_text
        #    pos = self.footer.edit_pos
        #    end_pos = len(text) - 1
        #    while pos < end_pos:
        #        self.footer.keypress((len(text),), "right")
        #        pos += 1
        #        if text[pos] == " ":
        #            break
        #        if pos == end_pos:
        #            self.footer.keypress((len(text),), "right")
        #            break

        elif key == "enter":
            # Parse data or (if parse failed)
            # send it to the current world
            text = self.footer.get_edit_text()

            with open("/tmp/pulsate.log", "a") as file:
                file.write(text + "\n")

            self.footer.set_edit_text(" "*len(text))
            self.footer.set_edit_text("")

            if text in ('quit', 'exit', ':q'):
                self.quit()

            elif text.startswith(":attach"):
                attachments = text.split(" ")[1:]
                for attachment in attachments:
                    logging.debug("Attachment: %s" % (attachment))

                loop = asyncio.get_event_loop()
                loop.create_task(self.send_message("", attachments))

            elif text.strip():
                #self.print_sent_message(text)

                loop = asyncio.get_event_loop()
                loop.create_task(self.send_message(text, []))

        else:
            self.context.keypress(size, key)

    def print_sent_message(self, text):
        """
            Print a received message
        """

        #self.print_text('[%s] You:' % self.get_time())
        #self.print_text(text)
        self.print_text("> %s" % text)
 
    def print_message(self, contact_name, text):
        """
            Print a sent message
        """

        #header = urwid.Text('%s:' % (message.timestamp, message.source))
        #header.set_align_mode('right')
        #self.print_text(header)
        #text = urwid.Text(message.text)
        #text.set_align_mode('right')

        text = "> %s" % text

        if contact_name:
            text = [("gray", contact_name), text]

        self.print_text(text)
        
    def print_text(self, text):
        """
            Print the given text in the _current_ window
            and scroll to the bottom. 
            You can pass a Text object or a string
        """

        walker = self.generic_output_walker

        if not isinstance(text, urwid.Text):
            text = urwid.Text(text)

        walker.append(text)

        self.body.scroll_to_bottom()


    def get_time(self):
        """
            Return formated current datetime
        """
        return datetime.datetime.now().strftime('%H:%M:%S')
        

def except_hook(extype, exobj, extb, manual=False):
    if not manual:
        try:
            main_window.quit(exit=False)
        except NameError:
            pass

    message = "An error occured:\n%(divider)s\n%(traceback)s\n"\
        "%(exception)s\n%(divider)s" % {
            "divider": 20*"-",
            "traceback": "".join(traceback.format_tb(extb)),
            "exception": extype.__name__+": "+str(exobj)
        }

    logging.error(message)

    print(message, file=sys.stderr)

def setup_logging(logfile):
    """ set the path of the logfile to tekka.logfile config
        value and create it (including path) if needed.
        After that, add a logging handler for exceptions
        which reports exceptions catched by the logger
        to the tekka_excepthook. (DBus uses this)
    """
    try:
        class ExceptionHandler(logging.Handler):
            """ handler for exceptions caught with logging.error.
                dump those exceptions to the exception handler.
            """
            def emit(self, record):
                if record.exc_info:
                    except_hook(*record.exc_info)

        logdir = os.path.dirname(logfile)

        if not os.path.exists(logdir):
            os.makedirs(logdir)

        logging.basicConfig(filename=logfile, level=logging.DEBUG,
            filemode="w")

        logging.getLogger("").addHandler(ExceptionHandler())

    except BaseException as e:
        print >> sys.stderr, "Logging init error: %s" % (e)


def main(argv):
    config = pulsate.load_config()

    if len(argv) == 2:
        choice = sys.argv[1]
    else:
        choice = None

    channel, is_group = pulsate.select_contact(choice, config)

    logfile = config["logfile"]
    setup_logging(logfile)

    main_window = MainWindow(config, channel, is_group)
    sys.excepthook = except_hook
    main_window.main()

if __name__ == "__main__":
    main(sys.argv)

