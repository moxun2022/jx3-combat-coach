"""JCL six-column parser. Explicit encoding; per-line error recovery."""
import codecs
import hashlib
import re
from typing import Protocol
from jx3_combat_coach.models import ParseError, ParseResult, RawEvent
from .lua import LuaReader


class Parser(Protocol):
    def parse(self, data: bytes, encoding: str = "utf-8-sig") -> ParseResult: ...


class JCLParser:
    def parse(self, data: bytes, encoding: str = "utf-8-sig") -> ParseResult:
        encoding = codecs.lookup(encoding).name
        if encoding not in {"utf-8", "utf-8-sig", "gbk", "gb18030"}:
            raise ValueError("unsupported encoding")
        digest = hashlib.sha256(data).hexdigest()
        result = ParseResult(source_sha256=digest, encoding=encoding, raw_hex=data.hex())
        lines = data.split(b"\n")
        if lines[-1] == b"":
            lines.pop()
        for number, raw in enumerate(lines, 1):
            try:
                line = raw.removesuffix(b"\r").decode(encoding)
                if number == 1:
                    line = line.removeprefix("\ufeff")
                columns = line.split("\t", 5)
                if len(columns) != 6 or any(re.fullmatch(r"-?[0-9]+", c) is None for c in columns[:5]):
                    raise ValueError("expected six columns with five integer headers")
                crc, frame, unix, client, code = map(int, columns[:5])
                payload = LuaReader(columns[5], encoding).parse()
                result.events.append(RawEvent(event_id=f"{digest}:{number}", line_number=number,
                    raw_line=line, crc=crc, logic_frame=frame, unix_seconds=unix,
                    client_ms=client, event_code=code, payload=payload))
            except (ValueError, RecursionError) as exc:
                result.errors.append(ParseError(line_number=number, raw_hex=raw.hex(), message=str(exc)))
        return result
