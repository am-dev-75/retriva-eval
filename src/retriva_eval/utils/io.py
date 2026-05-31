import json
import os
from typing import List, Any, TypeVar, Type
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

def write_jsonl(path: str, records: List[BaseModel]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(record.model_dump_json() + "\n")

def read_jsonl(path: str, model_class: Type[T]) -> List[T]:
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(model_class.model_validate_json(line))
    return records

def write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(data, BaseModel):
            f.write(data.model_dump_json(indent=2))
        else:
            json.dump(data, f, indent=2)

def read_json(path: str) -> Any:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
