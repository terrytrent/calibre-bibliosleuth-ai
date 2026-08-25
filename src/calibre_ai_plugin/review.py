import html
import copy
from urllib.parse import urlparse

from qt.core import (
    QBrush, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QHeaderView,
    QDesktopServices, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QTextBrowser, QUrl, QVBoxLayout, Qt, QListWidget, QTabWidget, QWidget,
    QShortcut, QKeySequence, QSizePolicy, QPalette,
)

from .constants import FIELD_NAMES
from .normalizer import display_value
from .normalizer import sanitize_comments
from .usage import PRICING_AS_OF, format_usage


def _open_evidence_url(parent, qurl):
    url = qurl.toString()
    host = urlparse(url).hostname or "unknown host"
    choice = QMessageBox.question(
        parent,
        "Open external evidence?",
        "This model-provided link will open in your browser:\n\n%s\n\nHost: %s\n\nContinue?" % (url, host),
    )
    if choice == QMessageBox.StandardButton.Yes:
        QDesktopServices.openUrl(QUrl(url))


def _secure_evidence_browser(parent=None):
    browser = QTextBrowser(parent)
    browser.setOpenLinks(False)
    browser.setOpenExternalLinks(False)
    browser.anchorClicked.connect(lambda url: _open_evidence_url(browser, url))
    return browser


def _source_label(url):
    host = (urlparse(url).hostname or "unknown source").lower().removeprefix("www.")
    if any(x in host for x in ("worldcat", "loc.gov", "library", "catalog")):
        kind = "Library catalog"
    elif any(x in host for x in ("isbn", "crossref")):
        kind = "Bibliographic registry"
    elif any(x in host for x in ("amazon", "barnesandnoble", "kobo", "bookshop")):
        kind = "Retailer"
    elif any(x in host for x in ("penguin", "harpercollins", "simonandschuster", "macmillan", "publisher")):
        kind = "Publisher"
    else:
        kind = "Web source"
    return "%s — %s" % (kind, host)


def _evidence_html(urls):
    return "<br>".join(
        '<a href="%s" title="%s">%s</a>' % (
            html.escape(url, quote=True), html.escape(url, quote=True), html.escape(_source_label(url)))
        for url in urls
    ) or "<i>No direct evidence; this value is inferred.</i>"


class TagEditorDialog(QDialog):
    def __init__(self, values, parent=None):
        super().__init__(parent); self.setWindowTitle("Edit proposed tags"); self.resize(520, 430)
        layout = QVBoxLayout(self); layout.addWidget(QLabel("One tag per row. Add, remove, or reorder the proposal."))
        self.tags = QListWidget(); self.tags.addItems(values or []); self.tags.setAccessibleName("Proposed tags"); layout.addWidget(self.tags)
        row = QHBoxLayout(); self.entry = QLineEdit(); self.entry.setPlaceholderText("New tag")
        add = QPushButton("Add"); remove = QPushButton("Remove selected")
        add.clicked.connect(self._add); self.entry.returnPressed.connect(self._add); remove.clicked.connect(self._remove)
        row.addWidget(self.entry); row.addWidget(add); row.addWidget(remove); layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def _add(self):
        value = self.entry.text().strip()
        if value and value.casefold() not in [self.tags.item(i).text().casefold() for i in range(self.tags.count())]:
            self.tags.addItem(value)
        self.entry.clear()

    def _remove(self):
        for item in self.tags.selectedItems(): self.tags.takeItem(self.tags.row(item))

    def value(self):
        return [self.tags.item(i).text() for i in range(self.tags.count())]


class DescriptionDialog(QDialog):
    def __init__(self, value, editable=False, parent=None):
        super().__init__(parent); self.setWindowTitle("Description preview" if not editable else "Edit proposed description")
        self.resize(760, 620); layout = QVBoxLayout(self); self.tabs = QTabWidget(); layout.addWidget(self.tabs)
        self.source = QPlainTextEdit(); self.source.setPlainText(value or ""); self.source.setReadOnly(not editable)
        self.preview = QTextBrowser(); self.tabs.addTab(self.preview, "Rendered"); self.tabs.addTab(self.source, "HTML source")
        self.count = QLabel(); layout.addWidget(self.count); self.source.textChanged.connect(self.refresh); self.tabs.currentChanged.connect(lambda *_: self.refresh()); self.refresh()
        standards = QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel if editable else QDialogButtonBox.StandardButton.Close
        buttons = QDialogButtonBox(standards); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def refresh(self):
        value = self.source.toPlainText(); self.preview.setHtml(sanitize_comments(value, 30000) or "<i>No description</i>")
        self.count.setText("%d characters · approximately %d words" % (len(value), len(value.split())))

    def value(self): return self.source.toPlainText().strip() or None


def review_field_names(result):
    names = [name for name in FIELD_NAMES if name in result["fields"]]
    series = result["fields"].get("series", {}).get("value")
    if "series" in names and series is not None:
        names.insert(names.index("series") + 1, "series_index")
    return names


def review_field(result, name):
    return result["fields"]["series" if name == "series_index" else name]


def review_value(data, name, proposed=False):
    if proposed:
        value = review_field(data, name)["value"]
    else:
        value = data.get("series" if name == "series_index" else name)
    if name == "series":
        return value.get("name") if value else None
    if name == "series_index":
        return value.get("index") if value else None
    return value


def display_review_value(data, name, proposed=False):
    value = review_value(data, name, proposed=proposed)
    if name == "authors" and isinstance(value, list):
        return " & ".join(map(str, value))
    return display_value(value)


class FieldOverrideDialog(QDialog):
    def __init__(self, field_name, value, parent=None):
        super().__init__(parent)
        self.field_name = field_name
        self.setWindowTitle("Override " + field_name.replace("_", " ").title())
        self.resize(620, 360 if field_name == "comments" else 220)
        layout = QVBoxLayout(self)
        self.name_edit = self.index_edit = None
        if field_name == "series":
            self.name_edit = QLineEdit(value or "")
            layout.addWidget(self.name_edit)
        elif field_name == "series_index":
            form = QFormLayout()
            self.index_edit = QDoubleSpinBox(); self.index_edit.setRange(-1, 100000); self.index_edit.setDecimals(2)
            self.index_edit.setSpecialValueText("No index"); self.index_edit.setValue(value if value is not None else -1)
            form.addRow("Series index", self.index_edit); layout.addLayout(form)
        else:
            self.editor = QPlainTextEdit()
            if field_name in ("authors", "tags"):
                self.editor.setPlaceholderText("Enter one value per line")
                self.editor.setPlainText("\n".join(value or []))
            elif field_name == "identifiers":
                self.editor.setPlaceholderText("Enter one identifier per line, for example: isbn:978... or asin:B0...")
                self.editor.setPlainText("\n".join("%s:%s" % (item.get("type", ""), item.get("value", "")) for item in (value or [])))
            else:
                self.editor.setPlainText(value or "")
            layout.addWidget(self.editor)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_if_valid); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def value(self):
        if self.field_name == "series":
            return self.name_edit.text().strip() or None
        if self.field_name == "series_index":
            return None if self.index_edit.value() < 0 else self.index_edit.value()
        text = self.editor.toPlainText().strip()
        if self.field_name in ("authors", "tags"):
            return [line.strip() for line in text.splitlines() if line.strip()]
        if self.field_name == "identifiers":
            result = []
            for line in text.splitlines():
                kind, separator, value = line.partition(":")
                if line.strip() and (not separator or not kind.strip() or not value.strip()):
                    raise ValueError("Each identifier must use type:value format: %s" % line)
                if line.strip():
                    result.append({"type": kind.strip().lower(), "value": value.strip()})
            return result
        return text or None

    def _accept_if_valid(self):
        try:
            self.value()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid override", str(exc)); return
        self.accept()


class FullReviewDialog(QDialog):
    def __init__(self, current, result, parent=None, usage=None, model="unknown"):
        super().__init__(parent)
        self.setWindowTitle("Full metadata comparison")
        self.resize(1100, 760)
        layout = QVBoxLayout(self)
        viewer = _secure_evidence_browser(self)
        sections = []
        for name in review_field_names(result):
            field = review_field(result, name)
            current_text = html.escape(display_review_value(current, name)) or "<i>Empty</i>"
            proposed_text = html.escape(display_review_value(result, name, proposed=True)) or "<i>Empty</i>"
            proposed_text = proposed_text.replace("\n", "<br>")
            current_text = current_text.replace("\n", "<br>")
            evidence = _evidence_html(field["evidence_urls"])
            confidence = "user override" if field.get("_user_override") else field["confidence"] + (" — inferred" if field["inferred"] else "")
            sections.append(
                "<h2>%s</h2><table width='100%%' cellspacing='8'>"
                "<tr><th width='18%%' align='left'>Current</th><td>%s</td></tr>"
                "<tr><th align='left'>Proposed</th><td>%s</td></tr>"
                "<tr><th align='left'>Confidence</th><td>%s</td></tr>"
                "<tr><th align='left'>Evidence</th><td>%s</td></tr></table><hr>"
                % (html.escape(name.replace("_", " ").title()), current_text, proposed_text, html.escape(confidence), evidence)
            )
        usage_html = "<h2>API usage</h2><p>%s</p><p><i>Cost is an estimate using standard pricing as of %s.</i></p><hr>" % (
            html.escape(format_usage(model, usage)), html.escape(PRICING_AS_OF)
        )
        viewer.setHtml(usage_html + "".join(sections)); layout.addWidget(viewer)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close); buttons.rejected.connect(self.reject); layout.addWidget(buttons)


class ReviewDialog(QDialog):
    PREVIOUS, APPLY_NEXT, SKIP_NEXT, FRESH, ACCEPT_REMAINING = 1001, 1002, 1003, 1004, 1005
    def __init__(self, title, current, result, parent=None, usage=None, model="unknown", batch_position=1, batch_total=1, selected=None):
        super().__init__(parent)
        self.current_data = copy.deepcopy(current)
        self.result_data = copy.deepcopy(result)
        self.original_result = copy.deepcopy(result)
        self.usage = usage or {}
        self.model = model
        self.review_fields = review_field_names(self.result_data)
        self.setWindowTitle("Review AI metadata — " + title)
        self.resize(1050, 650)
        layout = QVBoxLayout(self)
        match = result["match"]
        label = QLabel("Book %d of %d  ·  Match confidence: %s\n%s" % (batch_position, batch_total, match["edition_confidence"], match["candidate_identity"]))
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True); label.setMinimumWidth(0); label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred); layout.addWidget(label)
        rationale = QTextBrowser(); rationale.setPlainText(match["rationale"]); rationale.setMaximumHeight(95); rationale.setAccessibleName("Edition match rationale"); layout.addWidget(rationale)
        if result.get("_security_warning"):
            warning = QLabel(result["_security_warning"])
            warning.setTextFormat(Qt.TextFormat.PlainText)
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #b35a00; font-weight: bold;")
            layout.addWidget(warning)
        usage_label = QLabel(
            "API usage: %s\nEstimated cost uses standard pricing as of %s; actual billing may differ."
            % (format_usage(self.model, self.usage), PRICING_AS_OF)
        )
        usage_label.setWordWrap(True); layout.addWidget(usage_label)
        lookup = result.get("_lookup_info", {})
        if self.usage.get("cache_hit"):
            cache = QLabel("SESSION CACHE HIT · researched %s · %s · no new API charge" % (lookup.get("researched_at", "earlier this session"), lookup.get("model", model)))
            cache.setStyleSheet("background:#35633b;color:white;padding:6px;font-weight:bold;"); layout.addWidget(cache)
        self.table = QTableWidget(len(self.review_fields), 5)
        self.table.setHorizontalHeaderLabels(["Apply", "Field", "Current", "Proposed", "Confidence"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for row, name in enumerate(self.review_fields):
            field = review_field(self.result_data, name)
            value = review_value(self.result_data, name, proposed=True)
            check = QTableWidgetItem()
            flags = Qt.ItemFlag.ItemIsEnabled
            if value is not None:
                flags |= Qt.ItemFlag.ItemIsUserCheckable
            check.setFlags(flags)
            checked = name in selected if selected is not None else value is not None and field["confidence"] in ("high", "medium")
            check.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, check); self.table.setItem(row, 1, QTableWidgetItem(name.replace("_", " ").title()))
            self.table.setItem(row, 2, QTableWidgetItem(display_review_value(current, name)))
            proposed_item = QTableWidgetItem(display_review_value(self.result_data, name, proposed=True)); self.table.setItem(row, 3, proposed_item)
            unchanged = display_review_value(current, name).strip() == display_review_value(self.result_data, name, proposed=True).strip()
            if unchanged:
                proposed_item.setForeground(QBrush(self.table.palette().color(QPalette.ColorRole.PlaceholderText)))
            else:
                font = proposed_item.font(); font.setBold(True); proposed_item.setFont(font)
            confidence = ("[%s]" % field["confidence"].upper()) + (" · inferred" if field["inferred"] else "") + (" · unchanged" if unchanged else " · changed")
            confidence_item = QTableWidgetItem(confidence)
            self.table.setItem(row, 4, confidence_item)
        self.table.currentCellChanged.connect(self._show_evidence); layout.addWidget(self.table)
        self.table.setAccessibleName("Current and proposed metadata fields")
        select_row = QHBoxLayout()
        recommended = QPushButton("Select recommended"); recommended.clicked.connect(self.select_recommended)
        none = QPushButton("Select none"); none.clicked.connect(self.select_none)
        restore = QPushButton("Restore AI proposal"); restore.clicked.connect(self.restore_selected)
        fresh = QPushButton("Research fresh…"); fresh.clicked.connect(lambda: self.done(self.FRESH))
        for widget in (recommended, none, restore, fresh): select_row.addWidget(widget)
        select_row.addStretch(1); layout.addLayout(select_row)
        edit_row = QHBoxLayout()
        self.edit_button = QPushButton("Edit proposed value…"); self.edit_button.clicked.connect(self.edit_selected_field)
        self.full_review_button = QPushButton("View all details…"); self.full_review_button.clicked.connect(self.view_all_details)
        edit_row.addWidget(self.edit_button); edit_row.addWidget(self.full_review_button); edit_row.addStretch(1); layout.addLayout(edit_row)
        self.table.cellDoubleClicked.connect(self._double_clicked)
        self.evidence = _secure_evidence_browser(self); self.evidence.setMaximumHeight(120); layout.addWidget(self.evidence)
        nav = QHBoxLayout()
        self.previous_button = QPushButton("← Review previous book"); self.previous_button.setEnabled(batch_position > 1); self.previous_button.clicked.connect(lambda: self.done(self.PREVIOUS))
        self.accept_remaining_button = QPushButton("Accept all remaining books…")
        self.accept_remaining_button.setVisible(batch_position < batch_total)
        self.accept_remaining_button.setToolTip("Apply every non-empty proposal for this and all later books without reviewing them")
        self.accept_remaining_button.clicked.connect(lambda: self.done(self.ACCEPT_REMAINING))
        if batch_position < batch_total:
            skip_text = "Skip this book and review next →"
            apply_text = "Approve selected fields and review next →"
        else:
            skip_text = "Skip this book and finish"
            apply_text = "Approve selected fields and finish"
        self.skip_button = QPushButton(skip_text); self.skip_button.clicked.connect(lambda: self.done(self.SKIP_NEXT))
        self.apply_button = QPushButton(apply_text); self.apply_button.clicked.connect(lambda: self.done(self.APPLY_NEXT))
        nav.addWidget(self.previous_button); nav.addWidget(self.accept_remaining_button); nav.addStretch(1)
        nav.addWidget(self.skip_button); nav.addWidget(self.apply_button); layout.addLayout(nav)
        self.table.itemChanged.connect(self._selection_changed)
        self.table.setCurrentCell(0, 1)
        self._selection_changed()
        self.shortcuts = []
        for sequence, handler in (("Ctrl+Return", lambda: self.done(self.APPLY_NEXT)),
                                  ("Ctrl+Shift+A", self.select_recommended),
                                  ("Space", self.toggle_selected), ("Return", self.edit_selected_field)):
            shortcut = QShortcut(QKeySequence(sequence), self); shortcut.activated.connect(handler); self.shortcuts.append(shortcut)

    def _show_evidence(self, row, *_):
        if row < 0:
            return
        field = review_field(self.result_data, self.review_fields[row])
        if field["evidence_urls"]:
            self.evidence.setHtml("<b>Evidence</b><br>" + _evidence_html(field["evidence_urls"]))
        else:
            self.evidence.setPlainText("No direct evidence; this is an inference.")

    def selected_fields(self):
        return [name for row, name in enumerate(self.review_fields) if self.table.item(row, 0).checkState() == Qt.CheckState.Checked]

    def _selection_changed(self, *_):
        self.apply_button.setEnabled(bool(self.selected_fields()))

    def _double_clicked(self, row, column):
        if column in (1, 3):
            self.edit_field(row)

    def edit_selected_field(self):
        row = self.table.currentRow()
        if row >= 0:
            self.edit_field(row)

    def edit_field(self, row):
        name = self.review_fields[row]
        if name == "tags": editor = TagEditorDialog(review_value(self.result_data, name, proposed=True), self)
        elif name == "comments": editor = DescriptionDialog(review_value(self.result_data, name, proposed=True), True, self)
        else: editor = FieldOverrideDialog(name, review_value(self.result_data, name, proposed=True), self)
        if editor.exec() == QDialog.DialogCode.Accepted:
            self.set_override(row, editor.value())

    def set_override(self, row, value):
        name = self.review_fields[row]
        field = review_field(self.result_data, name)
        if name == "series":
            existing = field["value"] or {"name": None, "index": None}
            field["value"] = {"name": value, "index": existing.get("index")} if value else None
        elif name == "series_index":
            field["value"]["index"] = value
        else:
            field["value"] = value
        field["inferred"] = False
        field["evidence_urls"] = []
        field["_user_override"] = True
        self.table.item(row, 3).setText(display_review_value(self.result_data, name, proposed=True))
        self.table.item(row, 4).setText("user override")
        check = self.table.item(row, 0)
        check.setFlags(Qt.ItemFlag.ItemIsEnabled | (Qt.ItemFlag.ItemIsUserCheckable if value is not None else Qt.ItemFlag.NoItemFlags))
        check.setCheckState(Qt.CheckState.Checked if value is not None else Qt.CheckState.Unchecked)
        self._show_evidence(row)

    def select_recommended(self):
        for row, name in enumerate(self.review_fields):
            field = review_field(self.result_data, name); value = review_value(self.result_data, name, True)
            self.table.item(row, 0).setCheckState(Qt.CheckState.Checked if value is not None and field["confidence"] in ("high", "medium") else Qt.CheckState.Unchecked)

    def select_none(self):
        for row in range(len(self.review_fields)): self.table.item(row, 0).setCheckState(Qt.CheckState.Unchecked)

    def toggle_selected(self):
        row = self.table.currentRow()
        if row >= 0 and self.table.item(row, 0).flags() & Qt.ItemFlag.ItemIsUserCheckable:
            item = self.table.item(row, 0); item.setCheckState(Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked)

    def restore_selected(self):
        row = self.table.currentRow()
        if row < 0: return
        name = self.review_fields[row]; source = review_field(self.original_result, name); target = review_field(self.result_data, name)
        target.clear(); target.update(copy.deepcopy(source))
        self.table.item(row, 3).setText(display_review_value(self.result_data, name, True))
        self.table.item(row, 4).setText("[%s]%s" % (target["confidence"].upper(), " · inferred" if target["inferred"] else ""))
        self._show_evidence(row)

    def view_all_details(self):
        FullReviewDialog(self.current_data, self.result_data, self, self.usage, self.model).exec()
