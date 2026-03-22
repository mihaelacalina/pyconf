from typing import Any, Annotated, TypeAlias, get_origin
from dataclasses import dataclass


__all__ = ["Configuration", "ConfigSyntaxError", "Annotated"]

SerializableField: TypeAlias = bool | int | float | str

#region containers

@dataclass(slots = True)
class ConfigFileEmptyLines:
    count: int = 1

    def __str__(self):
        return "\n" * (self.count - 1)

@dataclass(slots = True)
class ConfigFileComment:
    message: str

    def __str__(self):
        pieces = []

        for line in self.message.split("\n"):
            pieces.append(f"#{line}\n")
        
        return "".join(pieces).removesuffix("\n")

@dataclass(slots = True)
class ConfigFileDeclaration:
    name: str
    value: str

    def __str__(self):
        return f"{self.name} = {self.value}"

#endregion

class Configuration:
    """
        Extend this class to create a configuration template and initialize it to load the file.
        
        The class docstring will be prepended to the configuration entries and
        all properties may have a comment attached by setting the type to `Annotated[type, "comment"]`.
    """

    _file_parts: list = []

    
    def __init__(self, file_path: str):
        from os.path import exists, isfile
        from os import access, R_OK


        option_types = self.__class__.__annotations__
        option_pairs = self.__class__.__dict__
        file_parts = self._file_parts


        super().__setattr__("_file_path", file_path)

        file_exists = exists(file_path)
        
        #region part initialization

        if file_exists:

            #region io checks

            if not isfile(file_path):
                raise RuntimeError(f"Configuration file {file_path} does not point ot a file")
            
            if not access(file_path, R_OK):
                raise IOError("Unable to access config file for reading")
        
            #endregion

            with open(file_path, "r") as handle:
                empty_count = 0

                for line_index, line in enumerate(handle, 1):
                    line = line.strip()
                    line_index += 1

                    #region empty lines

                    if len(line) < 1:
                        empty_count += 1
                        continue
                    else:
                        if empty_count > 0:
                            file_parts.append(ConfigFileEmptyLines(empty_count))

                        empty_count = 0

                    #endregion

                    #region comments

                    if line.startswith("#"):
                        file_parts.append(ConfigFileComment(line[1:]))

                        continue

                    #endregion

                    #region declarations

                    pieces = line.split("=", 1)

                    if len(pieces) < 2:
                        raise ConfigSyntaxError(f"Invalid syntax on line {line_index}")
                    
                    name = pieces[0].strip()
                    value = pieces[1].strip()
                    
                    file_parts.append(ConfigFileDeclaration(name, value))

                    #endregion
        else:
            if self.__doc__:
                for line in self.__doc__.strip("\n").strip().split("\n"):
                    file_parts.append(ConfigFileComment(" " + line.strip()))

                file_parts.append(ConfigFileEmptyLines(2))
            else:
                file_parts.append(ConfigFileEmptyLines(1))

        pad_line = not file_exists

        for option_name, option_default in option_pairs.items():
            found = False

            #region exclusions

            if option_name.startswith("_"):
                continue

            #region missing filter

            for entry in file_parts:
                if not isinstance(entry, ConfigFileDeclaration):
                    continue

                if entry.name == option_name:
                    found = True

            if found:
                continue

            #endregion

            #endregion

            #region pad line

            if not pad_line:
                pad_line = True

                file_parts.append(ConfigFileEmptyLines(1))
            
            #endregion

            option_type = option_types[option_name] if option_name in option_types else Any

            #region comments

            if get_origin(option_type) is Annotated:
                property_comment: str | None = option_type.__metadata__[0] if option_type.__metadata__ else None

                if isinstance(property_comment, str):
                    file_parts.append(ConfigFileComment(" " + property_comment))

            #endregion

            #region declarations

            self._set_value(option_name, option_default)
            file_parts.append(ConfigFileEmptyLines(1))

            #endregion

        #endregion

    def __setattr__(self, name: str, value: SerializableField):
        self._set_value(name, value)

    def __getattribute__(self, name: str):
        if name.startswith("_") or name in ["save"]:
            return super().__getattribute__(name)

        return self._get_value(name)


    def _get_type(self, name: str) -> type[SerializableField]:
        types = self.__class__.__annotations__
        option_type = types[name] if name in types else None

        if get_origin(option_type) is Annotated:
            return option_type.__origin__
        
        return option_type

    def _set_value(self, name: str, value: SerializableField):
        property_type = self._get_type(name)
        serialized_value = None

        #region checks

        if name not in self.__class__.__dict__.keys():
            raise KeyError(f"Undefined property {name}")

        if value is None:
            raise TypeError(f"Invalid type for property {name}: {type(value)}")

        if type(value) is not property_type:
            raise TypeError(f"Invalid type for property {name}: {type(value)}")
        
        if type(value) not in [bool, int, float, str]:
            raise TypeError(f"Illegal type for property {name}: {type(value)}")
        
        #endregion
        
        if property_type is bool:
            serialized_value = str("true" if bool(value) else "false")
        elif property_type is str:
            pieces = []

            #region string serializer

            # TODO-FUTURE: ADD SUPPORT FOR NON-PRINTING CHARACTERS

            translation_table = {
                "\n": "\\n",
                "\t": "\\t",
                "\0": "\\0",
                "\\": "\\\\",
                "\"" : "\\\"",
                "\033": "\\e"
            }

            for char in value:
                if char in translation_table.keys():
                    pieces.append(translation_table[char])
                    
                    continue

                pieces.append(char)

            #endregion
            
            serialized_value = "\"" + "".join(pieces) + "\""
        else:
            serialized_value = str(value)
        
        found = False
        
        for entry in self._file_parts:
            if not isinstance(entry, ConfigFileDeclaration):
                continue

            if entry.name == name:
                entry.value = serialized_value
                found = True

                break
        
        if not found:
            self._file_parts.append(ConfigFileDeclaration(name, serialized_value))

    def _get_value(self, name: str):
        property_type = self._get_type(name)
        raw_value: str = None

        #region checks

        if name not in self.__class__.__dict__.keys():
            raise KeyError(f"Undefined property {name}")
        
        #endregion

        for entry in self._file_parts:
            if not isinstance(entry, ConfigFileDeclaration):
                continue

            if entry.name == name:
                raw_value = entry.value

                break

        #     In all cases, the default value should have been loaded
        # as a config piece but who knows
         
        if raw_value is None:
            return super().__getattribute__(name)
        
        if property_type is int:
            try:
                return int(raw_value)
            except Exception as exception:
                raise ValueError(f"Invalid value for type int in property {name}") from exception
        elif property_type is float:
            try:
                return float(raw_value)
            except Exception as exception:
                raise ValueError(f"Invalid value for type float in property {name}") from exception
        elif property_type is bool:
            return raw_value.lower() == "true"
        elif property_type is str:
            escaped = False
            pieces = []

            if raw_value.startswith("\""):
                if not raw_value.endswith("\""):
                    raise ConfigSyntaxError(f"String missing end quote for property {name}")
                
                raw_value = raw_value[1:-1]


            for char in raw_value:
                if escaped:
                    if char == "n":
                        pieces.append("\n")
                    elif char == "t":
                        pieces.append("\t")
                    elif char == "0":
                        pieces.append("\0")
                    elif char == "\\":
                        pieces.append("\\")
                    elif char == "\"":
                        pieces.append("\"")
                    elif char == "e":
                        pieces.append("\033")
                    else:
                        pieces.append(char)
                    
                    escaped = False

                    continue

                if char == "\\":
                    escaped = True

                    continue

                pieces.append(char)

            return "".join(pieces)
        
        raise TypeError(f"Invalid type for property {name}")

    def get(self, name: str):
        """
            Returns the value stored for the given property.

            :raises KeyError: If the property is not defined in the template
            :raises ConfigSyntaxError: If the configuration line has a syntax error
            :raises ValueError: If the values in the configuration entry cannot be converted
            to the assigned type
            :raises TypeError: If the type defined in the template is not supported
        """

        return self._get_value(name)
    
    def set(self, name: str, value: SerializableField):
        """
            Sets the named property to the given value.

            :raises KeyError: If the property is not defined in the template
            :raises TypeError: If the type defined in the template is not the
            same as the one provided or if it's not supported
        """

        return self._set_value(name, value)

    def save(self):
        """
            Saves the configuration to the file, including all changes made during runtime.

            :raises IOError: If file writing cannot occur.
        """

        with open(super().__getattribute__("_file_path"), "w") as handle:
            for index, part in enumerate(self._file_parts):
                if index == len(self._file_parts) - 1:
                    handle.write(str(part))
                else:
                    handle.write(str(part) + "\n")

class ConfigSyntaxError(Exception):
    pass
