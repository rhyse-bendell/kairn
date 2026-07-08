from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QGroupBox, QLabel, QMessageBox, QPushButton, QTableWidgetItem, QVBoxLayout, QWidget, QHBoxLayout


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




def primary_cta_button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setMinimumHeight(50)
    button.setCursor(Qt.PointingHandCursor)
    font = button.font(); font.setBold(True); font.setPointSize(max(font.pointSize() + 2, 12)); button.setFont(font)
    button.setStyleSheet("""
        QPushButton { background-color: #2563eb; color: white; border: 1px solid #1d4ed8;
            border-radius: 12px; padding: 12px 20px; font-weight: 800; }
        QPushButton:hover { background-color: #1d4ed8; }
        QPushButton:pressed { background-color: #1e40af; }
        QPushButton:disabled { background-color: #9ca3af; border-color: #9ca3af; }
    """)
    return button


def secondary_button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setMinimumHeight(34)
    button.setCursor(Qt.PointingHandCursor)
    button.setStyleSheet("""
        QPushButton { background-color: #f9fafb; color: #111827; border: 1px solid #d1d5db;
            border-radius: 8px; padding: 7px 12px; }
        QPushButton:hover { background-color: #f3f4f6; }
    """)
    return button


def workflow_step_label(number: int, title: str, active: bool = False, complete: bool = False) -> QWidget:
    frame = QFrame(); layout = QHBoxLayout(frame); layout.setContentsMargins(8, 6, 8, 6); layout.setSpacing(6)
    state = "ACTIVE" if active else "DONE" if complete else "NEXT"
    badge = QLabel(str(number)); badge.setAlignment(Qt.AlignCenter); badge.setFixedSize(24, 24)
    label = QLabel(f"{title} · {state}")
    color = '#2563eb' if active else '#047857' if complete else '#6b7280'
    bg = '#eff6ff' if active else '#ecfdf5' if complete else '#f9fafb'
    frame.setStyleSheet(f"QFrame {{ background: {bg}; border: 1px solid {color}; border-radius: 10px; }} QLabel {{ color: #111827; font-weight: 600; }}")
    badge.setStyleSheet(f"background: {color}; color: white; border-radius: 12px; font-weight: 800;")
    layout.addWidget(badge); layout.addWidget(label)
    return frame


def workflow_card(title: str, description: str, button_text: str | None = None) -> QWidget:
    box = QGroupBox(title)
    box.setStyleSheet("QGroupBox { border: 1px solid #d1d5db; border-radius: 12px; margin-top: 10px; padding: 10px; font-weight: 700; background: #ffffff; } QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }")
    layout = QVBoxLayout(box)
    layout.addWidget(muted_help_label(description))
    if button_text:
        layout.addWidget(secondary_button(button_text))
    return box


def status_badge(text: str, kind: str) -> QLabel:
    colors = {
        'copied': ('#ecfdf5', '#047857'), 'linked': ('#eff6ff', '#1d4ed8'), 'ready': ('#ecfdf5', '#047857'),
        'warning': ('#fffbeb', '#b45309'), 'empty': ('#f3f4f6', '#4b5563'),
    }
    bg, fg = colors.get(kind, colors['empty'])
    label = QLabel(text); label.setStyleSheet(f"background: {bg}; color: {fg}; border: 1px solid {fg}; border-radius: 9px; padding: 2px 8px; font-size: 11px; font-weight: 800;")
    return label


def selected_item_panel(title: str, path: str | None, details: str | None = None) -> QGroupBox:
    box = QGroupBox(title); layout = QVBoxLayout(box)
    layout.addWidget(muted_help_label(details or (path or 'Select a file or folder in the Project Explorer to see available actions.')))
    return box

def muted_help_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet("color: #4b5563; font-size: 13px; line-height: 145%;")
    return label


def primary_action_button(text: str) -> QPushButton:
    return primary_cta_button(text)

def secondary_action_button(text: str) -> QPushButton:
    return secondary_button(text)

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
