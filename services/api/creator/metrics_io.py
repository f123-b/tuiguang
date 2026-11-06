import csv
import io
import json
import zipfile
from itertools import islice

from .errors import DomainError

FIELDS = (
    "content_id",
    "platform",
    "views",
    "likes",
    "saves",
    "clicks",
    "conversions",
    "period_start",
    "period_end",
    "observed_at",
)


async def read_upload(file):
    data = await file.read(5 * 1024 * 1024 + 1)
    if not data or len(data) > 5 * 1024 * 1024:
        raise DomainError("METRICS_FORMAT_INVALID", "报表须为非空文件且不超过 5 MB", 422)
    try:
        if (file.filename or "").lower().endswith(".xlsx"):
            import openpyxl

            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if sum(f.file_size for f in archive.infolist()) > 50 * 1024 * 1024:
                    raise ValueError("xlsx too large")
            book = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            try:
                iterator = book.active.iter_rows(values_only=True)
                header = [str(h).strip() if h is not None else "" for h in next(iterator)]
                raw = list(islice(iterator, 5001))
            finally:
                book.close()
        elif (file.filename or "").lower().endswith(".csv"):
            iterator = csv.reader(io.StringIO(data.decode("utf-8-sig")))
            header = [h.strip() for h in next(iterator)]
            raw = list(islice(iterator, 5001))
        else:
            raise ValueError("extension")
        if (
            not 1 <= len(header) <= 40
            or any(not h or len(h) > 120 for h in header)
            or len(set(header)) != len(header)
        ):
            raise ValueError("header")
        rows = [
            dict(zip(header, row)) for row in raw if any(value is not None and value != "" for value in row)
        ]
        if not rows or len(rows) > 5000:
            raise ValueError("rows")
        return header, rows
    except (ValueError, UnicodeError, OSError, StopIteration, zipfile.BadZipFile, KeyError):
        raise DomainError(
            "METRICS_FORMAT_INVALID",
            "无法读取报表：使用 UTF-8 CSV 或 XLSX，列名不可为空或重复，最多 40 列/5000 行",
            422,
        ) from None


def map_columns(header, rows, mapping):
    try:
        mapping = json.loads(mapping)
        if not isinstance(mapping, dict) or not set(mapping) <= set(FIELDS):
            raise ValueError("fields")
        if not mapping:
            return rows
        used = [value for value in mapping.values() if value]
        if any(value not in header for value in used) or len(set(used)) != len(used):
            raise ValueError("columns")
        return [{key: row.get(value) for key, value in mapping.items() if value} for row in rows]
    except (ValueError, TypeError):
        raise DomainError(
            "METRICS_MAPPING_INVALID", "请给每个指标匹配一个存在且不重复的文件列", 422
        ) from None
