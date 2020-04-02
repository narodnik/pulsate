![chat-window](https://raw.githubusercontent.com/narodnik/pulsate/master/screens/chat-window.png)

![show-window](https://github.com/narodnik/pulsate/blob/master/screens/show-window.png)

Python PIP dependencies (pip install --user <package>):

* python-magic
* sqlite3
* janus
* dbus-next
* iterfzf
* toml

You will need my hacked signal-cli:

$ git clone github.com/narodnik/signal-cli/
$ cd signal-cli
$ gradle build && gradle installDist
$ ./build/install/signal-cli/bin/signal-cli -u +12yoursignalnumber daemon

Also you will need to link signal (search the manual).

Then start the daemon in another window (or inside a screen session):

$ python pulsated.py

Now you can view your messages with the show utility:

$ python show.py

