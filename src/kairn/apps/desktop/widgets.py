from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QGroupBox, QLabel, QMessageBox, QPushButton, QTableWidgetItem, QVBoxLayout


def append_log(log_widget, message: str) -> None:
    log_widget.append(message)


def clear_table(table) -> None:
    table.setRowCount(0)


def dashboard_title_label(text: str) -> QLabel:
    label = QLabel(text)
    font = QFont()
    font.setPointSize(34)
    font.setBold(True)
    label.setFont(font)
    label.setStyleSheet("color: #111827;")
    return label


def dashboard_description_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setMaximumWidth(900)
    label.setStyleSheet(
        "font-size: 18px; line-height: 150%; color: #374151; padding-top: 4px; padding-bottom: 8px;"
    )
    return label


def landing_button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setMinimumSize(290, 60)
    button.setCursor(Qt.PointingHandCursor)
    button.setStyleSheet(
        """
        QPushButton {
            background-color: #1f4ed8;
            border: 1px solid #1d4ed8;
            border-radius: 10px;
            color: white;
            font-size: 17px;
            font-weight: 700;
            padding: 14px 22px;
        }
        QPushButton:hover {
            background-color: #1d45bf;
        }
        QPushButton:pressed {
            background-color: #1e3a8a;
        }
        """
    )
    return button



def muted_help_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet("color: #4b5563; font-size: 13px; line-height: 145%;")
    return label


def primary_action_button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setMinimumHeight(44)
    button.setCursor(Qt.PointingHandCursor)
    font = button.font()
    font.setBold(True)
    font.setPointSize(max(font.pointSize() + 1, 11))
    button.setFont(font)
    button.setStyleSheet("QPushButton { padding: 10px 16px; border-radius: 6px; font-weight: 700; }")
    return button


def secondary_action_button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setMinimumHeight(30)
    button.setCursor(Qt.PointingHandCursor)
    button.setStyleSheet("QPushButton { padding: 6px 10px; }")
    return button


def page_header(title: str, description: str, primary_action_text: str | None = None) -> QWidget:
    frame = QFrame()
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(0, 0, 0, 10)
    title_label = QLabel(title)
    font = QFont()
    font.setPointSize(22)
    font.setBold(True)
    title_label.setFont(font)
    desc = muted_help_label(description)
    layout.addWidget(title_label)
    layout.addWidget(desc)
    if primary_action_text:
        label = muted_help_label(f"Primary action: {primary_action_text}")
        label.setStyleSheet("color: #111827; font-size: 13px; font-weight: 700;")
        layout.addWidget(label)
    return frame


def section_header(title: str, description: str | None = None) -> QWidget:
    frame = QFrame()
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(0, 0, 0, 4)
    label = QLabel(title)
    font = label.font()
    font.setBold(True)
    font.setPointSize(max(font.pointSize() + 1, 11))
    label.setFont(font)
    layout.addWidget(label)
    if description:
        layout.addWidget(muted_help_label(description))
    return frame


def action_tile(title: str, description: str, button_text: str | None = None) -> QWidget:
    box = QGroupBox(title)
    layout = QVBoxLayout(box)
    layout.addWidget(muted_help_label(description))
    if button_text:
        layout.addWidget(secondary_action_button(button_text))
    return box


def callout_box(title: str, body: str) -> QGroupBox:
    box = QGroupBox(title)
    layout = QVBoxLayout(box)
    layout.addWidget(muted_help_label(body))
    return box

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
