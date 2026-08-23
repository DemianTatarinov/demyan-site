#!/usr/bin/env python3
"""
Fedora / Wayland Modern PDF Editor & Cropper (PyQt6 + PyMuPDF)
"""

import sys
import fitz  # PyMuPDF
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QPen, QColor, QBrush, QPainter, QAction
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsRectItem, QFileDialog, QMessageBox,
    QToolBar, QLabel, QComboBox, QStatusBar
)


class PDFCanvasScene(QGraphicsScene):
    """Interactive graphics scene for rendering PDF pages and handling selections."""
    selection_changed = pyqtSignal()

    MODE_NAVIGATE = 0
    MODE_CROP = 1
    MODE_HIGHLIGHT = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = self.MODE_NAVIGATE
        self.pixmap_item = None
        self.start_point = None
        self.current_rect_item = None

        # Crop rectangle item (single active crop area)
        self.crop_rect_item = None
        self.crop_rect = None  # QRectF in scene coords

        # Highlight rectangles items (list of QRectF and graphics items)
        self.highlight_items = []
        self.highlight_rects = []  # List of QRectF in scene coords

    def set_pixmap(self, pixmap):
        self.clear_all()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.addItem(self.pixmap_item)
        self.setSceneRect(QRectF(pixmap.rect()))

    def clear_all(self):
        self.clear()
        self.pixmap_item = None
        self.crop_rect_item = None
        self.crop_rect = None
        self.highlight_items.clear()
        self.highlight_rects.clear()

    def set_mode(self, mode):
        self.mode = mode

    def mousePressEvent(self, event):
        if not self.pixmap_item or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        pos = event.scenePos()
        # Ensure within pixmap bounds
        if not self.pixmap_item.boundingRect().contains(pos):
            return

        if self.mode in (self.MODE_CROP, self.MODE_HIGHLIGHT):
            self.start_point = pos
            rect = QRectF(self.start_point, self.start_point)

            if self.mode == self.MODE_CROP:
                if self.crop_rect_item:
                    self.removeItem(self.crop_rect_item)
                    self.crop_rect_item = None
                pen = QPen(QColor(55, 129, 226), 2, Qt.PenStyle.DashLine)
                brush = QBrush(QColor(55, 129, 226, 40))
                self.current_rect_item = QGraphicsRectItem(rect)
                self.current_rect_item.setPen(pen)
                self.current_rect_item.setBrush(brush)
                self.addItem(self.current_rect_item)

            elif self.mode == self.MODE_HIGHLIGHT:
                pen = QPen(QColor(255, 215, 0), 1, Qt.PenStyle.SolidLine)
                brush = QBrush(QColor(255, 235, 59, 100))
                self.current_rect_item = QGraphicsRectItem(rect)
                self.current_rect_item.setPen(pen)
                self.current_rect_item.setBrush(brush)
                self.addItem(self.current_rect_item)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.start_point and self.current_rect_item:
            current_pos = event.scenePos()
            # Constrain to pixmap bounds
            bounds = self.pixmap_item.boundingRect()
            clamped_x = max(bounds.left(), min(current_pos.x(), bounds.right()))
            clamped_y = max(bounds.top(), min(current_pos.y(), bounds.bottom()))
            clamped_pos = QPointF(clamped_x, clamped_y)

            rect = QRectF(self.start_point, clamped_pos).normalized()
            self.current_rect_item.setRect(rect)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.start_point and self.current_rect_item:
            rect = self.current_rect_item.rect().normalized()
            if rect.width() > 5 and rect.height() > 5:
                if self.mode == self.MODE_CROP:
                    self.crop_rect_item = self.current_rect_item
                    self.crop_rect = rect
                elif self.mode == self.MODE_HIGHLIGHT:
                    self.highlight_items.append(self.current_rect_item)
                    self.highlight_rects.append(rect)
            else:
                self.removeItem(self.current_rect_item)

            self.start_point = None
            self.current_rect_item = None
            self.selection_changed.emit()
        else:
            super().mouseReleaseEvent(event)

    def clear_crop(self):
        if self.crop_rect_item:
            self.removeItem(self.crop_rect_item)
            self.crop_rect_item = None
            self.crop_rect = None
            self.selection_changed.emit()

    def clear_highlights(self):
        for item in self.highlight_items:
            self.removeItem(item)
        self.highlight_items.clear()
        self.highlight_rects.clear()
        self.selection_changed.emit()


class PDFEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fedora PDF Crop & Annotate")
        self.resize(1100, 800)

        self.doc = None
        self.file_path = None
        self.current_page_idx = 0
        self.zoom_factor = 2.0  # Render resolution multiplier for high DPI display

        self.scene = PDFCanvasScene(self)
        self.scene.selection_changed.connect(self.update_status_bar)

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setCentralWidget(self.view)

        self._create_toolbar()
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready. Open a PDF document to begin.")

    def _create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # File actions
        open_act = QAction("Open PDF", self)
        open_act.setStatusTip("Open a PDF file")
        open_act.triggered.connect(self.open_file)
        toolbar.addAction(open_act)

        save_act = QAction("Save As PDF", self)
        save_act.setStatusTip("Save modified/cropped document as a new PDF file")
        save_act.triggered.connect(self.save_as)
        toolbar.addAction(save_act)

        toolbar.addSeparator()

        # Mode selection
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Navigate / View", "Select Crop Area", "Highlight Area"])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        toolbar.addWidget(QLabel(" Mode: "))
        toolbar.addWidget(self.mode_combo)

        toolbar.addSeparator()

        # Clear actions
        clear_crop_act = QAction("Clear Crop", self)
        clear_crop_act.triggered.connect(self.scene.clear_crop)
        toolbar.addAction(clear_crop_act)

        clear_hl_act = QAction("Clear Highlights", self)
        clear_hl_act.triggered.connect(self.scene.clear_highlights)
        toolbar.addAction(clear_hl_act)

        toolbar.addSeparator()

        # Page navigation
        self.prev_act = QAction("◀ Prev", self)
        self.prev_act.triggered.connect(self.prev_page)
        self.prev_act.setEnabled(False)
        toolbar.addAction(self.prev_act)

        self.page_label = QLabel(" Page 0 / 0 ")
        toolbar.addWidget(self.page_label)

        self.next_act = QAction("Next ▶", self)
        self.next_act.triggered.connect(self.next_page)
        self.next_act.setEnabled(False)
        toolbar.addAction(self.next_act)

    def on_mode_changed(self, index):
        self.scene.set_mode(index)
        if index == PDFCanvasScene.MODE_CROP:
            self.statusBar.showMessage("Mode: Crop. Click and drag to select a cropping boundary.")
        elif index == PDFCanvasScene.MODE_HIGHLIGHT:
            self.statusBar.showMessage("Mode: Highlight. Click and drag to highlight areas.")
        else:
            self.statusBar.showMessage("Mode: Navigation.")

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF Document", "", "PDF Files (*.pdf)"
        )
        if not file_path:
            return  # User canceled dialog gracefully

        try:
            doc = fitz.open(file_path)
            if doc.is_encrypted:
                QMessageBox.warning(self, "Encrypted PDF", "Encrypted/password-protected PDFs are not supported.")
                return

            self.doc = doc
            self.file_path = file_path
            self.current_page_idx = 0
            self.render_current_page()
            self.statusBar.showMessage(f"Loaded: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error Loading PDF", f"Failed to open PDF file:\n{str(e)}")

    def render_current_page(self):
        if not self.doc or len(self.doc) == 0:
            return

        page = self.doc[self.current_page_idx]
        mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=mat)

        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        qpixmap = QPixmap.fromImage(img)

        self.scene.set_pixmap(qpixmap)
        self.page_label.setText(f" Page {self.current_page_idx + 1} / {len(self.doc)} ")

        self.prev_act.setEnabled(self.current_page_idx > 0)
        self.next_act.setEnabled(self.current_page_idx < len(self.doc) - 1)

    def prev_page(self):
        if self.doc and self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.render_current_page()

    def next_page(self):
        if self.doc and self.current_page_idx < len(self.doc) - 1:
            self.current_page_idx += 1
            self.render_current_page()

    def update_status_bar(self):
        msg = f"Page {self.current_page_idx + 1} of {len(self.doc) if self.doc else 0}"
        if self.scene.crop_rect:
            msg += " | Crop Box Set"
        if self.scene.highlight_rects:
            msg += f" | {len(self.scene.highlight_rects)} Highlight(s)"
        self.statusBar.showMessage(msg)

    def save_as(self):
        if not self.doc:
            QMessageBox.information(self, "No Document", "Please open a PDF file first.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Modified PDF As", "", "PDF Files (*.pdf)"
        )
        if not save_path:
            return  # User canceled save dialog gracefully

        try:
            out_doc = fitz.open(self.file_path)

            # Apply crop box if specified on current page
            if self.scene.crop_rect:
                crop_qrect = self.scene.crop_rect
                scale = 1.0 / self.zoom_factor
                pdf_rect = fitz.Rect(
                    crop_qrect.left() * scale,
                    crop_qrect.top() * scale,
                    crop_qrect.right() * scale,
                    crop_qrect.bottom() * scale
                )
                page = out_doc[self.current_page_idx]
                page.set_cropbox(pdf_rect)

            # Apply highlights on current page
            if self.scene.highlight_rects:
                page = out_doc[self.current_page_idx]
                scale = 1.0 / self.zoom_factor
                for hl_qrect in self.scene.highlight_rects:
                    pdf_rect = fitz.Rect(
                        hl_qrect.left() * scale,
                        hl_qrect.top() * scale,
                        hl_qrect.right() * scale,
                        hl_qrect.bottom() * scale
                    )
                    annot = page.add_highlight_annot(pdf_rect)
                    annot.update()

            out_doc.save(save_path, garbage=4, deflate=True)
            out_doc.close()

            QMessageBox.information(
                self, "Success", f"File saved successfully to:\n{save_path}"
            )
            self.statusBar.showMessage(f"Saved: {save_path}")

        except Exception as e:
            QMessageBox.critical(
                self, "Save Error", f"Failed to save modified PDF:\n{str(e)}"
            )


def main():
    app = QApplication(sys.argv)
    window = PDFEditorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
