#!/usr/bin/env python3
"""
Fedora / Wayland Modern PDF Continuous-Scroll Editor & Cross-Page Cropper (PyQt6 + PyMuPDF)
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


class ContinuousPDFCanvasScene(QGraphicsScene):
    """Interactive graphics scene rendering all PDF pages in a continuous vertical column."""
    selection_changed = pyqtSignal()

    MODE_NAVIGATE = 0
    MODE_CROP = 1
    MODE_HIGHLIGHT = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = self.MODE_NAVIGATE
        self.start_point = None
        self.current_rect_item = None

        # Items and data tracking
        self.page_items = []      # List of (page_num, QGraphicsPixmapItem, QRectF scene_rect)
        self.crop_rect_item = None
        self.crop_rect = None     # QRectF in scene coords

        self.highlight_items = []
        self.highlight_rects = [] # List of QRectF in scene coords

    def clear_all(self):
        self.clear()
        self.page_items.clear()
        self.crop_rect_item = None
        self.crop_rect = None
        self.highlight_items.clear()
        self.highlight_rects.clear()

    def set_mode(self, mode):
        self.mode = mode

    def mousePressEvent(self, event):
        if not self.page_items or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        pos = event.scenePos()

        if self.mode in (self.MODE_CROP, self.MODE_HIGHLIGHT):
            self.start_point = pos
            rect = QRectF(self.start_point, self.start_point)

            if self.mode == self.MODE_CROP:
                if self.crop_rect_item:
                    self.removeItem(self.crop_rect_item)
                    self.crop_rect_item = None
                self.crop_rect = None
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
            # Constrain to total scene bounds
            bounds = self.sceneRect()
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
                if self.mode == self.MODE_CROP:
                    self.crop_rect = None

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
        self.setWindowTitle("Fedora PDF Continuous Scroll Editor & Cross-Page Cropper")
        self.resize(1150, 850)

        self.doc = None
        self.file_path = None
        self.zoom_factor = 2.0  # High DPI rendering multiplier
        self.page_spacing = 15  # Margin between pages in continuous scroll

        self.scene = ContinuousPDFCanvasScene(self)
        self.scene.selection_changed.connect(self.update_status_bar)

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setCentralWidget(self.view)

        self._create_toolbar()
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready. Open a PDF document to view pages continuously.")

    def _create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # File actions
        open_act = QAction("Open PDF", self)
        open_act.setStatusTip("Open a PDF file")
        open_act.triggered.connect(self.open_file)
        toolbar.addAction(open_act)

        save_act = QAction("Save Crop / Annotations As PDF", self)
        save_act.setStatusTip("Export cropped section (including cross-page selections) as a new PDF file")
        save_act.triggered.connect(self.save_as)
        toolbar.addAction(save_act)

        toolbar.addSeparator()

        # Mode selection
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Pan / Scroll Document", "Select Cross-Page Crop", "Highlight Selection"])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        toolbar.addWidget(QLabel(" Tool Mode: "))
        toolbar.addWidget(self.mode_combo)

        toolbar.addSeparator()

        # Clear actions
        clear_crop_act = QAction("Clear Crop Selection", self)
        clear_crop_act.triggered.connect(self.scene.clear_crop)
        toolbar.addAction(clear_crop_act)

        clear_hl_act = QAction("Clear Highlights", self)
        clear_hl_act.triggered.connect(self.scene.clear_highlights)
        toolbar.addAction(clear_hl_act)

        toolbar.addSeparator()

        self.doc_info_label = QLabel(" Document: None ")
        toolbar.addWidget(self.doc_info_label)

    def on_mode_changed(self, index):
        self.scene.set_mode(index)
        if index == ContinuousPDFCanvasScene.MODE_CROP:
            self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.statusBar.showMessage("Mode: Crop. Drag across pages to select any area to crop.")
        elif index == ContinuousPDFCanvasScene.MODE_HIGHLIGHT:
            self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.statusBar.showMessage("Mode: Highlight. Drag across any area to add a visual highlight.")
        else:
            self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.statusBar.showMessage("Mode: Pan / Scroll Document. Click and drag to scroll.")

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
            self.render_continuous_document()
            self.doc_info_label.setText(f" Document: {len(doc)} Page(s) ")
            self.statusBar.showMessage(f"Loaded: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error Loading PDF", f"Failed to open PDF file:\n{str(e)}")

    def render_continuous_document(self):
        if not self.doc or len(self.doc) == 0:
            return

        self.scene.clear_all()

        current_y = 0.0
        max_width = 0.0

        for page_idx, page in enumerate(self.doc):
            mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            pix = page.get_pixmap(matrix=mat)

            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            qpixmap = QPixmap.fromImage(img)

            pixmap_item = QGraphicsPixmapItem(qpixmap)
            pixmap_item.setPos(0, current_y)
            self.scene.addItem(pixmap_item)

            scene_rect = QRectF(0, current_y, pix.width, pix.height)
            self.scene.page_items.append((page_idx, pixmap_item, scene_rect))

            if pix.width > max_width:
                max_width = float(pix.width)

            current_y += pix.height + self.page_spacing

        total_height = max(0.0, current_y - self.page_spacing)
        self.scene.setSceneRect(0, 0, max_width, total_height)

    def update_status_bar(self):
        msg = f"Document: {len(self.doc) if self.doc else 0} Pages (Continuous Scroll)"
        if self.scene.crop_rect:
            r = self.scene.crop_rect
            msg += f" | Crop Selection Set: {int(r.width())}x{int(r.height())} px"
        if self.scene.highlight_rects:
            msg += f" | {len(self.scene.highlight_rects)} Highlight(s)"
        self.statusBar.showMessage(msg)

    def save_as(self):
        if not self.doc:
            QMessageBox.information(self, "No Document", "Please open a PDF file first.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Cropped / Annotated PDF As", "", "PDF Files (*.pdf)"
        )
        if not save_path:
            return  # User canceled dialog gracefully

        try:
            out_doc = fitz.open()

            # If user made a specific crop selection (which can span page boundaries)
            if self.scene.crop_rect:
                crop_rect = self.scene.crop_rect.normalized()

                # Render the selected scene region directly from scene/page pixmaps
                scale = 1.0 / self.zoom_factor
                target_width_pts = crop_rect.width() * scale
                target_height_pts = crop_rect.height() * scale

                # Create target page in output PDF with exact dimensions of crop rectangle
                new_page = out_doc.new_page(width=target_width_pts, height=target_height_pts)

                for page_idx, pixmap_item, page_scene_rect in self.scene.page_items:
                    # Check intersection between crop selection and current page in scene coords
                    intersect_scene = crop_rect.intersected(page_scene_rect)
                    if not intersect_scene.isEmpty():
                        # Determine local crop rect relative to top-left of this page
                        local_crop = QRectF(
                            intersect_scene.left() - page_scene_rect.left(),
                            intersect_scene.top() - page_scene_rect.top(),
                            intersect_scene.width(),
                            intersect_scene.height()
                        )

                        # Convert to PDF page coordinates (points)
                        src_pdf_rect = fitz.Rect(
                            local_crop.left() * scale,
                            local_crop.top() * scale,
                            local_crop.right() * scale,
                            local_crop.bottom() * scale
                        )

                        # Destination position on the output page
                        dest_x = (intersect_scene.left() - crop_rect.left()) * scale
                        dest_y = (intersect_scene.top() - crop_rect.top()) * scale
                        dest_pdf_rect = fitz.Rect(
                            dest_x,
                            dest_y,
                            dest_x + (intersect_scene.width() * scale),
                            dest_y + (intersect_scene.height() * scale)
                        )

                        # Draw cropped portion from original page onto the output single-page PDF
                        new_page.show_pdf_page(dest_pdf_rect, self.doc, page_idx, clip=src_pdf_rect)

                # Apply highlight annotations falling within crop rect onto the output page
                for hl_rect in self.scene.highlight_rects:
                    intersect_hl = crop_rect.intersected(hl_rect)
                    if not intersect_hl.isEmpty():
                        hl_x = (intersect_hl.left() - crop_rect.left()) * scale
                        hl_y = (intersect_hl.top() - crop_rect.top()) * scale
                        dest_hl_rect = fitz.Rect(
                            hl_x,
                            hl_y,
                            hl_x + (intersect_hl.width() * scale),
                            hl_y + (intersect_hl.height() * scale)
                        )
                        annot = new_page.add_highlight_annot(dest_hl_rect)
                        annot.update()

            else:
                # No crop selection: export full document with applied highlights
                out_doc.close()
                out_doc = fitz.open(self.file_path)
                scale = 1.0 / self.zoom_factor

                for hl_rect in self.scene.highlight_rects:
                    for page_idx, pixmap_item, page_scene_rect in self.scene.page_items:
                        intersect = hl_rect.intersected(page_scene_rect)
                        if not intersect.isEmpty():
                            local_hl = QRectF(
                                intersect.left() - page_scene_rect.left(),
                                intersect.top() - page_scene_rect.top(),
                                intersect.width(),
                                intersect.height()
                            )
                            pdf_rect = fitz.Rect(
                                local_hl.left() * scale,
                                local_hl.top() * scale,
                                local_hl.right() * scale,
                                local_hl.bottom() * scale
                            )
                            page = out_doc[page_idx]
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
