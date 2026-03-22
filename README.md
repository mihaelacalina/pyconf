# pyconf
Lightweight configuration loader with type checking and templates

### Current features:
* **Type checking for simple types** ( `string`, `int`, `float`, `bool` )
* **Docstrings and comments in template are written to the config file**
* **Configuration values may be changed from the code**
* **Config file creation based on template**

### Limitations:
* **All properties must have a default value**
* **`None` values are not supported**

### Requirements
* **Python 3.9+** (For `typing.Annotated` support)

### Examples:
The following is a simple program that reads the configuration and changes a value
```py
from pyconf import *


class AppConfig(Configuration):
    """
        Logger configuration

        Default configuration can be found at /usr/local/etc/logger.conf.default
    """
    
    file_location: Annotated[str, "The path to the log file"] = "/var/run/logger.log"
    file_max_size: Annotated[int, "The maximum size of the log file, in kilobytes"] = 16

    debug: bool = False

# Load configuration
config = AppConfig("config.conf")

# Read a value from the configuration file
print(config.debug)

# Entries may be modified from code and
# the file will reflect the change
config.debug = True

# Saves all changes to the file
config.save()
```

The program will produce the following configuration file:

```ini
# Logger configuration
# 
# Default configuration can be found at /usr/local/etc/logger.conf.default


# The path to the log file
file_location = "/var/run/logger.log"

# The maximum size of the log file, in kilobytes
file_max_size = 16

debug = true
```