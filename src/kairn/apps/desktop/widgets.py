from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QTableWidgetItem


def append_log(log_widget, message: str) -> None:
    log_widget.append(message)


def clear_table(table) -> None:
    table.setRowCount(0)


def set_table_rows(table, rows, columns) -> None:
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.setRowCount(len(rows))
    for i, row in enumerate(rows):
        for j, col in enumerate(columns):
            table.setItem(i, j, QTableWidgetItem(str(row.get(col, "") or "")))


def selected_table_row_data(table):
    idx = table.currentRow()
    if idx < 0:
        return None
    row = {}
    for j in range(table.columnCount()):
        header = table.horizontalHeaderItem(j).text()
        item = table.item(idx, j)
        row[header] = item.text() if item else ""
    return row


def open_path(path: str) -> None:
    p = Path(path)
    if not p.exists():
        return
    if sys.platform.startswith("win"):
        os.startfile(str(p))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(p)])
    else:
        subprocess.Popen(["xdg-open", str(p)])


def safe_count_label(label, name: str, value) -> None:
    label.setText(f"{name}: {value if value is not None else 0}")


def show_error(parent, title: str, message: str) -> None:
    QMessageBox.critical(parent, title, message)


def show_info(parent, title: str, message: str) -> None:
    QMessageBox.information(parent, title, message)
