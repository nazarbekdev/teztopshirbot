#!/usr/bin/env python3
"""
Bazaning kunlik zaxira nusxasi (cron). Baza pul va balanslarni saqlaydi — yo'qolsa tiklab bo'lmaydi.

`sqlite3.Connection.backup` ishlayotgan bazadan ham izchil nusxa oladi (WAL bilan xavfsiz); oddiy `cp` esa
yozuv o'rtasida buzuq fayl berishi mumkin. Oxirgi 14 nusxa saqlanadi.
"""

import datetime
import pathlib
import sqlite3
import sys

DB = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/lib/teztopshir/teztopshir.db")
OUT = DB.parent / "backups"
KEEP = 14

OUT.mkdir(exist_ok=True)
target = OUT / f"{DB.stem}-{datetime.date.today().isoformat()}.db"
source, dest = sqlite3.connect(DB), sqlite3.connect(target)
with dest:
    source.backup(dest)
source.close()
dest.close()
target.chmod(0o600)
for old in sorted(OUT.glob(f"{DB.stem}-*.db"))[:-KEEP]:
    old.unlink()
print("zaxira:", target, target.stat().st_size, "bayt")
