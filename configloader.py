from configparser import ConfigParser, NoOptionError
import os


class Config:
    """Interact with configuration variables."""

    configParser = ConfigParser()

    @classmethod
    def __init__(self, path='config.ini'):
        """Start config by reading config.ini."""
        self.configParser.read(os.path.join(os.getcwd(), path))

    @classmethod
    def gwb(self, key):
        """Get values from config.ini from the project GalizanWarBot."""
        try:
            return self.configParser.get('GalizanWarBot', key)
        except NoOptionError:
            return None
