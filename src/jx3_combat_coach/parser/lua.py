"""Parse a restricted Lua data grammar without evaluating Lua code.

Tables use ordered key/value pairs, retaining duplicate keys and explicit nil.
Unsupported syntax is reported, never executed or silently repaired.
"""
import math
import re


class LuaReader:
    def __init__(self, text: str, encoding: str):
        self.text, self.encoding, self.pos = text, encoding, 0

    def space(self):
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.pos += 1

    def take(self, token: str) -> bool:
        self.space()
        if self.text.startswith(token, self.pos):
            self.pos += len(token)
            return True
        return False

    def require(self, token: str):
        if not self.take(token):
            raise ValueError(f"expected {token!r} at offset {self.pos}")

    def string(self):
        quote = self.text[self.pos]
        self.pos += 1
        result = bytearray()
        escapes = {"a": 7, "b": 8, "f": 12, "n": 10, "r": 13, "t": 9, "v": 11}
        encoding = "utf-8" if self.encoding == "utf-8-sig" else self.encoding
        while self.pos < len(self.text):
            char = self.text[self.pos]
            self.pos += 1
            if char == quote:
                return result.decode(encoding)
            if char == "\\":
                if self.pos >= len(self.text):
                    break
                char = self.text[self.pos]
                self.pos += 1
                if char.isascii() and char.isdigit():
                    digits = char
                    while len(digits) < 3 and self.pos < len(self.text) and self.text[self.pos] in "0123456789":
                        digits += self.text[self.pos]
                        self.pos += 1
                    number = int(digits)
                    if number > 255:
                        raise ValueError("byte escape exceeds 255")
                    result.append(number)
                    continue
                if char in escapes:
                    result.append(escapes[char])
                    continue
                if char not in ("\\", "'", '"'):
                    raise ValueError("unsupported string escape")
            result.extend(char.encode(encoding))
        raise ValueError("unterminated string")

    def value(self, depth=0):
        self.space()
        if depth > 64:
            raise ValueError("Lua nesting exceeds 64")
        if self.take("{"):
            entries, index = [], 1
            while not self.take("}"):
                if self.take("["):
                    key = self.value(depth + 1)
                    if type(key) not in (int, float, str):
                        raise ValueError("unsupported table key")
                    self.require("]")
                    self.require("=")
                else:
                    key, index = index, index + 1
                entries.append([key, self.value(depth + 1)])
                if self.take("}"):
                    break
                if not (self.take(",") or self.take(";")):
                    raise ValueError("expected table separator")
            return {"$table": entries}
        if self.pos < len(self.text) and self.text[self.pos] in ("'", '"'):
            return self.string()
        match = re.match(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", self.text[self.pos:])
        if match:
            token = match.group()
            self.pos += len(token)
            value = float(token) if any(c in token.lower() for c in ".e") else int(token)
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("non-finite number")
            return value
        for token, value in (("true", True), ("false", False), ("nil", None)):
            if self.take(token):
                return value
        raise ValueError(f"unsupported Lua literal at offset {self.pos}")

    def parse(self):
        result = self.value()
        self.space()
        if self.pos != len(self.text) or not isinstance(result, dict):
            raise ValueError("payload must be one Lua table")
        return result
