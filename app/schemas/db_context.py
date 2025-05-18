from dataclasses import dataclass
from typing import Any, Dict

__all__ = ["DBContext"]

@dataclass
class DBContext:
    """資料庫上下文依賴類別。"""

    connection: Any
    schema_info: Dict[str, Any]

