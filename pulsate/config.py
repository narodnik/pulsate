import toml

def load_config():
    with open("config.toml", "r") as file:
        config = toml.loads(file.read())
    return config

