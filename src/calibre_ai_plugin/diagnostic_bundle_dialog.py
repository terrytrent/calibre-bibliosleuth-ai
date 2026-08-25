from qt.core import (
    QCheckBox, QDialog, QFileDialog, QLabel, QMessageBox, QPushButton, QTextBrowser,
    QVBoxLayout, QHBoxLayout,
)


class DiagnosticBundleDialog(QDialog):
    def __init__(self, journal, context, parent=None):
        super().__init__(parent); self.journal = journal; self.context = context
        self.setWindowTitle("Collect BiblioSleuth AI diagnostic logs"); self.resize(720, 560)
        layout = QVBoxLayout(self)
        heading = QLabel("Preview diagnostic bundle"); font = heading.font(); font.setBold(True); font.setPointSize(font.pointSize() + 2); heading.setFont(font)
        layout.addWidget(heading)
        preview = QTextBrowser(); preview.setHtml(
            "<p>The locally saved ZIP will contain:</p><ul>"
            "<li><b>README.txt</b> — sharing and privacy guidance</li>"
            "<li><b>manifest.json</b> — bundle version and contents</li>"
            "<li><b>environment.json</b> — versions, platform, redacted configuration, aggregate statistics, and cache state</li>"
            "<li><b>recent-journal.json</b> — up to 20 sanitized job summaries from the last 7 days</li></ul>"
            "<p><b>Never included:</b> API keys, authorization headers, titles, authors, library paths/IDs, EPUB text or metadata values, full prompts, model responses, evidence URLs, or credential-vault contents.</p>"
            "<p>Nothing is uploaded automatically. Review the ZIP before sharing it.</p>"
        ); layout.addWidget(preview)
        self.details = QCheckBox("Include exact sanitized error messages and stack traces")
        self.details.setChecked(True); layout.addWidget(self.details)
        count = len(journal.entries()); self.count_label = QLabel("Recent journal entries available: %d" % count); layout.addWidget(self.count_label)
        buttons = QHBoxLayout(); clear = QPushButton("Clear recent logs…"); clear.clicked.connect(self.clear_logs)
        save = QPushButton("Save diagnostic ZIP…"); save.clicked.connect(self.save_bundle)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        buttons.addWidget(clear); buttons.addStretch(1); buttons.addWidget(cancel); buttons.addWidget(save); layout.addLayout(buttons)

    def clear_logs(self):
        if QMessageBox.question(self, "Clear diagnostic history?", "Permanently delete all retained BiblioSleuth AI diagnostic journal entries?") != QMessageBox.StandardButton.Yes: return
        count = self.journal.clear(); self.count_label.setText("Recent journal entries available: 0")
        QMessageBox.information(self, "Diagnostic history cleared", "Deleted %d journal entry or entries." % count)

    def save_bundle(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save BiblioSleuth AI diagnostic bundle", "BiblioSleuth AI-diagnostics.zip", "ZIP archives (*.zip)")
        if not path: return
        if not path.lower().endswith(".zip"): path += ".zip"
        try:
            files = self.journal.export_zip(path, self.context, self.details.isChecked())
        except Exception as exc:
            QMessageBox.critical(self, "Could not save diagnostics", str(exc)); return
        QMessageBox.information(self, "Diagnostic bundle saved", "Saved %d files to:\n%s\n\nNothing was uploaded." % (len(files), path)); self.accept()
