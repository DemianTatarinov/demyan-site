#!/usr/bin/env python3
"""
Fedora / Wayland Modern PDF Continuous-Scroll Editor, Cropper, Merger & Redactor
Features:
1. Merge PDFs functionality
2. Russian UI by default
3. Language toggle (RU / EN) without restart
4. Zoom via Ctrl + Mouse Wheel
5. Dynamic Zoom Percentage indicator
6. Page Rotation (90°) and Page Deletion for visible/centered page
7. Area-based Text Extraction directly to system clipboard
8. Erase / Redact Selected Area permanently using PyMuPDF
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

# Translation dictionary for localization (Russian / English)
TRANSLATIONS = {
    "RU": {
        "title": "Редактор и Кроппер PDF (Fedora Wayland)",
        "open": "Открыть PDF",
        "open_tip": "Открыть один PDF файл",
        "merge": "Объединить PDF",
        "merge_tip": "Объединить несколько PDF файлов в один",
        "save": "Сохранить Документ / Кроп / Аннотации",
        "save_tip": "Экспортировать выбранную область кроппинга или сохранить изменения документа в новый PDF файл",
        "mode_label": " Режим инструмента: ",
        "mode_nav": "Панорамирование / Просмотр",
        "mode_crop": "Выделение Кропа (Межстраничное)",
        "mode_hl": "Выделение Маркером",
        "mode_extract": "Извлечение Текста",
        "mode_erase": "Стереть / Редактировать область",
        "rotate": "Повернуть 90°",
        "rotate_tip": "Повернуть текущую видимую страницу на 90 градусов по часовой стрелке",
        "delete_page": "Удалить Страницу",
        "delete_page_tip": "Удалить текущую видимую страницу из документа",
        "clear_crop": "Сбросить Кроп",
        "clear_hl": "Сбросить Маркеры",
        "lang_label": " Язык / Lang: ",
        "doc_none": " Документ: Не загружен ",
        "doc_pages": " Документ: {} стр. ",
        "ready_status": "Готово. Откройте PDF документ для работы.",
        "mode_crop_msg": "Режим: Кроп. Выделите область (можно через границы страниц) для обрезки.",
        "mode_hl_msg": "Режим: Маркер. Выделите область для подсветки текста.",
        "mode_extract_msg": "Режим: Извлечение Текста. Выделите прямоугольником текст для копирования в буфер обмена.",
        "mode_erase_msg": "Режим: Стереть область. Выделите прямоугольником содержимое для полного удаления (редактирования).",
        "mode_nav_msg": "Режим: Просмотр. Зажмите левую кнопку мыши для перемещения. Ctrl + Колесико для масштаба.",
        "status_base": "Документ: {} стр. (Непрерывная прокрутка)",
        "status_crop": " | Область кропа: {}x{} px",
        "status_hl": " | Выделений маркером: {}",
        "zoom_label": " Масштаб: {}%",
        "text_copied": "Скопировано в буфер обмена ({} симв.)",
        "text_no_found": "В выделенной области текст не найден",
        "area_erased": "Выбранная область успешно удалена (стирание зафиксировано)",
        "msg_encrypted_title": "Зашифрованный PDF",
        "msg_encrypted_body": "Зашифрованные или защищенные паролем PDF файлы не поддерживаются.",
        "msg_err_open_title": "Ошибка открытия PDF",
        "msg_err_open_body": "Не удалось открыть PDF файл:\n{}",
        "msg_no_doc_title": "Нет документа",
        "msg_no_doc_body": "Пожалуйста, сначала откройте PDF файл.",
        "msg_save_ok_title": "Успешно сохранено",
        "msg_save_ok_body": "Файл успешно сохранен в:\n{}",
        "msg_save_err_title": "Ошибка сохранения",
        "msg_save_err_body": "Не удалось сохранить PDF файл:\n{}",
        "msg_merge_select": "Выберите PDF файлы для объединения",
        "msg_merge_save": "Сохранить объединенный PDF как",
        "msg_merge_need_two": "Для объединения необходимо выбрать минимум 2 PDF файла.",
        "msg_merge_ok_title": "Объединение завершено",
        "msg_merge_ok_body": "Объединенный файл успешно сохранен в:\n{}",
        "msg_merge_err_title": "Ошибка объединения",
        "msg_merge_err_body": "Не удалось объединить PDF файлы:\n{}",
        "msg_confirm_del_title": "Подтверждение удаления",
        "msg_confirm_del_body": "Вы уверены, что хотите удалить страницу {}?"
    },
    "EN": {
        "title": "Fedora PDF Editor & Cross-Page Cropper",
        "open": "Open PDF",
        "open_tip": "Open a single PDF file",
        "merge": "Merge PDFs",
        "merge_tip": "Combine multiple PDF files into one",
        "save": "Save Document / Crop / Annotations",
        "save_tip": "Export cropped selection or save modified document to a new PDF file",
        "mode_label": " Tool Mode: ",
        "mode_nav": "Pan / View Document",
        "mode_crop": "Select Cross-Page Crop",
        "mode_hl": "Highlight Selection",
        "mode_extract": "Extract Text",
        "mode_erase": "Erase / Redact Area",
        "rotate": "Rotate 90°",
        "rotate_tip": "Rotate currently visible page 90 degrees clockwise",
        "delete_page": "Delete Page",
        "delete_page_tip": "Delete currently visible page from document",
        "clear_crop": "Clear Crop",
        "clear_hl": "Clear Highlights",
        "lang_label": " Language / Язык: ",
        "doc_none": " Document: None ",
        "doc_pages": " Document: {} Page(s) ",
        "ready_status": "Ready. Open a PDF document to begin.",
        "mode_crop_msg": "Mode: Crop. Drag across pages to select any area to crop.",
        "mode_hl_msg": "Mode: Highlight. Drag across any area to add a visual highlight.",
        "mode_extract_msg": "Mode: Extract Text. Drag a rectangle over text to copy it to system clipboard.",
        "mode_erase_msg": "Mode: Erase Area. Drag a rectangle over content to permanently redact/blank it out.",
        "mode_nav_msg": "Mode: View. Click and drag to scroll. Ctrl + Mouse Wheel to zoom.",
        "status_base": "Document: {} Pages (Continuous Scroll)",
        "status_crop": " | Crop Selection Set: {}x{} px",
        "status_hl": " | Highlight(s): {}",
        "zoom_label": " Zoom: {}%",
        "text_copied": "Text copied to clipboard ({} chars)",
        "text_no_found": "No text found in selected region",
        "area_erased": "Selected area successfully redacted/erased",
        "msg_encrypted_title": "Encrypted PDF",
        "msg_encrypted_body": "Encrypted/password-protected PDFs are not supported.",
        "msg_err_open_title": "Error Loading PDF",
        "msg_err_open_body": "Failed to open PDF file:\n{}",
        "msg_no_doc_title": "No Document",
        "msg_no_doc_body": "Please open a PDF file first.",
        "msg_save_ok_title": "Success",
        "msg_save_ok_body": "File saved successfully to:\n{}",
        "msg_save_err_title": "Save Error",
        "msg_save_err_body": "Failed to save modified PDF:\n{}",
        "msg_merge_select": "Select PDF Files to Merge",
        "msg_merge_save": "Save Merged PDF As",
        "msg_merge_need_two": "Please select at least 2 PDF files to merge.",
        "msg_merge_ok_title": "Merge Complete",
        "msg_merge_ok_body": "Merged file saved successfully to:\n{}",
        "msg_merge_err_title": "Merge Error",
        "msg_merge_err_body": "Failed to merge PDF files:\n{}",
        "msg_confirm_del_title": "Confirm Deletion",
        "msg_confirm_del_body": "Are you sure you want to delete page {}?"
    }
}


class PDFGraphicsView(QGraphicsView):
    """Custom QGraphicsView with Ctrl + Mouse Wheel zoom support and zoom signal reporting."""
    zoom_changed = pyqtSignal(float)

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.current_zoom = 1.0

    def wheelEvent(self, event):
        # Feature 4: Zoom via Ctrl + Mouse Wheel
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            zoom_in_factor = 1.15
            zoom_out_factor = 1.0 / zoom_in_factor

            if event.angleDelta().y() > 0:
                self.scale(zoom_in_factor, zoom_in_factor)
                self.current_zoom *= zoom_in_factor
            else:
                self.scale(zoom_out_factor, zoom_out_factor)
                self.current_zoom *= zoom_out_factor

            # Feature 5: Report zoom change
            self.zoom_changed.emit(self.current_zoom)
            event.accept()
        else:
            # Standard vertical scrolling when Ctrl is not pressed
            super().wheelEvent(event)


class ContinuousPDFCanvasScene(QGraphicsScene):
    """Interactive graphics scene rendering all PDF pages in a continuous vertical column."""
    selection_changed = pyqtSignal()
    text_extracted = pyqtSignal(str)
    request_render = pyqtSignal()

    MODE_NAVIGATE = 0
    MODE_CROP = 1
    MODE_HIGHLIGHT = 2
    MODE_EXTRACT_TEXT = 3
    MODE_ERASE = 4  # Feature 8: Redact/Erase selected area

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mode = self.MODE_NAVIGATE
        self.start_point = None
        self.current_rect_item = None
        self.doc_ref = None    # Reference to PyMuPDF document
        self.zoom_factor = 2.0 # High DPI scale factor

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

        if self.mode in (self.MODE_CROP, self.MODE_HIGHLIGHT, self.MODE_EXTRACT_TEXT, self.MODE_ERASE):
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

            elif self.mode == self.MODE_EXTRACT_TEXT:
                pen = QPen(QColor(46, 125, 50), 2, Qt.PenStyle.DotLine)
                brush = QBrush(QColor(76, 175, 80, 40))
                self.current_rect_item = QGraphicsRectItem(rect)
                self.current_rect_item.setPen(pen)
                self.current_rect_item.setBrush(brush)
                self.addItem(self.current_rect_item)

            elif self.mode == self.MODE_ERASE:
                pen = QPen(QColor(211, 47, 47), 2, Qt.PenStyle.SolidLine)
                brush = QBrush(QColor(239, 83, 80, 80))
                self.current_rect_item = QGraphicsRectItem(rect)
                self.current_rect_item.setPen(pen)
                self.current_rect_item.setBrush(brush)
                self.addItem(self.current_rect_item)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.start_point and self.current_rect_item:
            current_pos = event.scenePos()
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

                elif self.mode == self.MODE_EXTRACT_TEXT:
                    extracted_parts = []
                    scale = 1.0 / self.zoom_factor
                    if self.doc_ref:
                        for page_idx, item, page_scene_rect in self.page_items:
                            intersect = rect.intersected(page_scene_rect)
                            if not intersect.isEmpty():
                                local_rect = QRectF(
                                    intersect.left() - page_scene_rect.left(),
                                    intersect.top() - page_scene_rect.top(),
                                    intersect.width(),
                                    intersect.height()
                                )
                                pdf_rect = fitz.Rect(
                                    local_rect.left() * scale,
                                    local_rect.top() * scale,
                                    local_rect.right() * scale,
                                    local_rect.bottom() * scale
                                )
                                text = self.doc_ref[page_idx].get_text("text", clip=pdf_rect)
                                if text:
                                    extracted_parts.append(text.strip())

                    full_text = "\n".join(extracted_parts)
                    self.removeItem(self.current_rect_item)
                    self.text_extracted.emit(full_text)

                elif self.mode == self.MODE_ERASE:
                    # Feature 8: Permanently redact/erase selected area
                    scale = 1.0 / self.zoom_factor
                    if self.doc_ref:
                        for page_idx, item, page_scene_rect in self.page_items:
                            intersect = rect.intersected(page_scene_rect)
                            if not intersect.isEmpty():
                                local_rect = QRectF(
                                    intersect.left() - page_scene_rect.left(),
                                    intersect.top() - page_scene_rect.top(),
                                    intersect.width(),
                                    intersect.height()
                                )
                                pdf_rect = fitz.Rect(
                                    local_rect.left() * scale,
                                    local_rect.top() * scale,
                                    local_rect.right() * scale,
                                    local_rect.bottom() * scale
                                )
                                page = self.doc_ref[page_idx]
                                page.add_redact_annot(pdf_rect, fill=(1, 1, 1))
                                page.apply_redactions()

                    self.removeItem(self.current_rect_item)
                    self.request_render.emit()

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
        # Feature 2: Russian interface by default
        self.current_lang = "RU"

        self.doc = None
        self.file_path = None
        self.zoom_factor = 2.0  # High DPI rendering multiplier
        self.page_spacing = 15  # Margin between pages in continuous scroll

        self.scene = ContinuousPDFCanvasScene(self)
        self.scene.selection_changed.connect(self.update_status_bar)
        self.scene.text_extracted.connect(self.handle_extracted_text)
        self.scene.request_render.connect(self.on_erased_re_render)

        self.view = PDFGraphicsView(self.scene, self)
        self.view.zoom_changed.connect(self.update_zoom_indicator)
        self.setCentralWidget(self.view)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # Feature 5: Zoom percentage indicator widget in status bar
        self.zoom_indicator = QLabel(" Zoom: 100% ", self)
        self.statusBar.addPermanentWidget(self.zoom_indicator)

        self._create_toolbar()
        self.update_ui_text()

    def tr(self, key):
        """Fetch localized string for active language."""
        return TRANSLATIONS.get(self.current_lang, TRANSLATIONS["RU"]).get(key, "")

    def _create_toolbar(self):
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        # File actions
        self.open_act = QAction(self)
        self.open_act.triggered.connect(self.open_file)
        self.toolbar.addAction(self.open_act)

        # Feature 1: Merge PDFs Action
        self.merge_act = QAction(self)
        self.merge_act.triggered.connect(self.merge_pdfs)
        self.toolbar.addAction(self.merge_act)

        self.save_act = QAction(self)
        self.save_act.triggered.connect(self.save_as)
        self.toolbar.addAction(self.save_act)

        self.toolbar.addSeparator()

        # Tool Mode selection
        self.mode_label = QLabel(self)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["", "", "", "", ""])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.toolbar.addWidget(self.mode_label)
        self.toolbar.addWidget(self.mode_combo)

        self.toolbar.addSeparator()

        # Feature 6: Page Rotation and Page Deletion Actions
        self.rotate_act = QAction(self)
        self.rotate_act.triggered.connect(self.rotate_current_page)
        self.toolbar.addAction(self.rotate_act)

        self.delete_page_act = QAction(self)
        self.delete_page_act.triggered.connect(self.delete_current_page)
        self.toolbar.addAction(self.delete_page_act)

        self.toolbar.addSeparator()

        # Clear actions
        self.clear_crop_act = QAction(self)
        self.clear_crop_act.triggered.connect(self.scene.clear_crop)
        self.toolbar.addAction(self.clear_crop_act)

        self.clear_hl_act = QAction(self)
        self.clear_hl_act.triggered.connect(self.scene.clear_highlights)
        self.toolbar.addAction(self.clear_hl_act)

        self.toolbar.addSeparator()

        # Feature 3: Language Toggle Selector (RU / EN)
        self.lang_label = QLabel(self)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Русский (RU)", "English (EN)"])
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        self.toolbar.addWidget(self.lang_label)
        self.toolbar.addWidget(self.lang_combo)

        self.toolbar.addSeparator()

        self.doc_info_label = QLabel(self)
        self.toolbar.addWidget(self.doc_info_label)

    def update_ui_text(self):
        """Feature 3: Dynamically updates all UI texts for current language without restart."""
        self.setWindowTitle(self.tr("title"))

        self.open_act.setText(self.tr("open"))
        self.open_act.setStatusTip(self.tr("open_tip"))

        self.merge_act.setText(self.tr("merge"))
        self.merge_act.setStatusTip(self.tr("merge_tip"))

        self.save_act.setText(self.tr("save"))
        self.save_act.setStatusTip(self.tr("save_tip"))

        self.rotate_act.setText(self.tr("rotate"))
        self.rotate_act.setStatusTip(self.tr("rotate_tip"))

        self.delete_page_act.setText(self.tr("delete_page"))
        self.delete_page_act.setStatusTip(self.tr("delete_page_tip"))

        self.mode_label.setText(self.tr("mode_label"))

        self.mode_combo.blockSignals(True)
        curr_idx = self.mode_combo.currentIndex()
        self.mode_combo.clear()
        self.mode_combo.addItems([
            self.tr("mode_nav"),
            self.tr("mode_crop"),
            self.tr("mode_hl"),
            self.tr("mode_extract"),
            self.tr("mode_erase")
        ])
        self.mode_combo.setCurrentIndex(max(0, curr_idx))
        self.mode_combo.blockSignals(False)

        self.clear_crop_act.setText(self.tr("clear_crop"))
        self.clear_hl_act.setText(self.tr("clear_hl"))

        self.lang_label.setText(self.tr("lang_label"))

        if self.doc:
            self.doc_info_label.setText(self.tr("doc_pages").format(len(self.doc)))
        else:
            self.doc_info_label.setText(self.tr("doc_none"))

        self.update_zoom_indicator(self.view.current_zoom)
        self.update_status_bar()

    def update_zoom_indicator(self, zoom_scale):
        """Feature 5: Update zoom percentage indicator dynamically."""
        percent = int(zoom_scale * 100)
        self.zoom_indicator.setText(self.tr("zoom_label").format(percent))

    def on_language_changed(self, index):
        """Handles language toggle changes."""
        self.current_lang = "RU" if index == 0 else "EN"
        self.update_ui_text()

    def on_mode_changed(self, index):
        self.scene.set_mode(index)
        if index == ContinuousPDFCanvasScene.MODE_CROP:
            self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.statusBar.showMessage(self.tr("mode_crop_msg"))
        elif index == ContinuousPDFCanvasScene.MODE_HIGHLIGHT:
            self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.statusBar.showMessage(self.tr("mode_hl_msg"))
        elif index == ContinuousPDFCanvasScene.MODE_EXTRACT_TEXT:
            self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.statusBar.showMessage(self.tr("mode_extract_msg"))
        elif index == ContinuousPDFCanvasScene.MODE_ERASE:
            self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.statusBar.showMessage(self.tr("mode_erase_msg"))
        else:
            self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.statusBar.showMessage(self.tr("mode_nav_msg"))

    def get_most_visible_page_index(self):
        """Feature 6 Helper: Determines which page is centered/most visible in viewport."""
        if not self.doc or not self.scene.page_items:
            return 0

        viewport_center = self.view.viewport().rect().center()
        scene_center = self.view.mapToScene(viewport_center)

        for page_idx, item, scene_rect in self.scene.page_items:
            if scene_rect.contains(scene_center):
                return page_idx

        min_dist = float('inf')
        closest_idx = 0
        for page_idx, item, scene_rect in self.scene.page_items:
            dist = abs(scene_rect.center().y() - scene_center.y())
            if dist < min_dist:
                min_dist = dist
                closest_idx = page_idx
        return closest_idx

    def rotate_current_page(self):
        """Feature 6: Rotate currently visible page 90 degrees clockwise."""
        if not self.doc or len(self.doc) == 0:
            QMessageBox.information(self, self.tr("msg_no_doc_title"), self.tr("msg_no_doc_body"))
            return

        page_idx = self.get_most_visible_page_index()
        page = self.doc[page_idx]
        current_rot = page.rotation
        page.set_rotation((current_rot + 90) % 360)

        self.render_continuous_document()

    def delete_current_page(self):
        """Feature 6: Delete currently visible page from document."""
        if not self.doc or len(self.doc) == 0:
            QMessageBox.information(self, self.tr("msg_no_doc_title"), self.tr("msg_no_doc_body"))
            return

        if len(self.doc) == 1:
            QMessageBox.warning(self, self.tr("delete_page"), "Cannot delete the only page in document.")
            return

        page_idx = self.get_most_visible_page_index()
        confirm = QMessageBox.question(
            self,
            self.tr("msg_confirm_del_title"),
            self.tr("msg_confirm_del_body").format(page_idx + 1),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.doc.delete_page(page_idx)
            self.render_continuous_document()
            self.doc_info_label.setText(self.tr("doc_pages").format(len(self.doc)))

    def handle_extracted_text(self, text):
        """Feature 7: Copy extracted text to system clipboard and notify in status bar."""
        if text:
            QApplication.clipboard().setText(text)
            self.statusBar.showMessage(self.tr("text_copied").format(len(text)), 4000)
        else:
            self.statusBar.showMessage(self.tr("text_no_found"), 4000)

    def on_erased_re_render(self):
        """Feature 8 Helper: Re-renders document after applying redaction and updates status bar."""
        self.render_continuous_document()
        self.statusBar.showMessage(self.tr("area_erased"), 4000)

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("open"), "", "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        try:
            doc = fitz.open(file_path)
            if doc.is_encrypted:
                QMessageBox.warning(self, self.tr("msg_encrypted_title"), self.tr("msg_encrypted_body"))
                return

            self.doc = doc
            self.scene.doc_ref = doc
            self.file_path = file_path
            self.render_continuous_document()
            self.doc_info_label.setText(self.tr("doc_pages").format(len(doc)))
            self.statusBar.showMessage(f"{self.tr('open')}: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, self.tr("msg_err_open_title"), self.tr("msg_err_open_body").format(str(e)))

    def merge_pdfs(self):
        """Feature 1: Select multiple PDF files and merge them into a single file."""
        files, _ = QFileDialog.getOpenFileNames(
            self, self.tr("msg_merge_select"), "", "PDF Files (*.pdf)"
        )
        if not files or len(files) < 2:
            if files:
                QMessageBox.information(self, self.tr("merge"), self.tr("msg_merge_need_two"))
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("msg_merge_save"), "", "PDF Files (*.pdf)"
        )
        if not save_path:
            return

        try:
            merged_doc = fitz.open()
            for pdf_file in files:
                curr_doc = fitz.open(pdf_file)
                merged_doc.insert_pdf(curr_doc)
                curr_doc.close()

            merged_doc.save(save_path, garbage=4, deflate=True)
            merged_doc.close()

            QMessageBox.information(
                self, self.tr("msg_merge_ok_title"), self.tr("msg_merge_ok_body").format(save_path)
            )

            # Auto-open merged document
            self.doc = fitz.open(save_path)
            self.scene.doc_ref = self.doc
            self.file_path = save_path
            self.render_continuous_document()
            self.doc_info_label.setText(self.tr("doc_pages").format(len(self.doc)))

        except Exception as e:
            QMessageBox.critical(
                self, self.tr("msg_merge_err_title"), self.tr("msg_merge_err_body").format(str(e))
            )

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
        if not self.doc:
            self.statusBar.showMessage(self.tr("ready_status"))
            return

        msg = self.tr("status_base").format(len(self.doc))
        if self.scene.crop_rect:
            r = self.scene.crop_rect
            msg += self.tr("status_crop").format(int(r.width()), int(r.height()))
        if self.scene.highlight_rects:
            msg += self.tr("status_hl").format(len(self.scene.highlight_rects))
        self.statusBar.showMessage(msg)

    def save_as(self):
        if not self.doc:
            QMessageBox.information(self, self.tr("msg_no_doc_title"), self.tr("msg_no_doc_body"))
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("save"), "", "PDF Files (*.pdf)"
        )
        if not save_path:
            return

        try:
            # Cross-page crop region export logic
            if self.scene.crop_rect:
                out_doc = fitz.open()
                crop_rect = self.scene.crop_rect.normalized()
                scale = 1.0 / self.zoom_factor
                target_width_pts = crop_rect.width() * scale
                target_height_pts = crop_rect.height() * scale

                new_page = out_doc.new_page(width=target_width_pts, height=target_height_pts)

                for page_idx, pixmap_item, page_scene_rect in self.scene.page_items:
                    intersect_scene = crop_rect.intersected(page_scene_rect)
                    if not intersect_scene.isEmpty():
                        local_crop = QRectF(
                            intersect_scene.left() - page_scene_rect.left(),
                            intersect_scene.top() - page_scene_rect.top(),
                            intersect_scene.width(),
                            intersect_scene.height()
                        )
                        src_pdf_rect = fitz.Rect(
                            local_crop.left() * scale,
                            local_crop.top() * scale,
                            local_crop.right() * scale,
                            local_crop.bottom() * scale
                        )
                        dest_x = (intersect_scene.left() - crop_rect.left()) * scale
                        dest_y = (intersect_scene.top() - crop_rect.top()) * scale
                        dest_pdf_rect = fitz.Rect(
                            dest_x,
                            dest_y,
                            dest_x + (intersect_scene.width() * scale),
                            dest_y + (intersect_scene.height() * scale)
                        )
                        new_page.show_pdf_page(dest_pdf_rect, self.doc, page_idx, clip=src_pdf_rect)

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
                # Save modified self.doc directly to preserve in-memory page rotations, deletions, and redactions
                out_doc = self.doc
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
            if self.scene.crop_rect:
                out_doc.close()

            QMessageBox.information(
                self, self.tr("msg_save_ok_title"), self.tr("msg_save_ok_body").format(save_path)
            )
            self.statusBar.showMessage(f"{self.tr('save')}: {save_path}")

        except Exception as e:
            QMessageBox.critical(
                self, self.tr("msg_save_err_title"), self.tr("msg_save_err_body").format(str(e))
            )


def main():
    app = QApplication(sys.argv)
    window = PDFEditorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
