import html

from qt.core import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget,
    QTextBrowser, QVBoxLayout, QWidget,
)

from .metrics import filter_records, group_summaries, summarize
from .usage import PRICING_AS_OF


def _duration(value):
    if value is None: return "—"
    value = float(value)
    if value >= 60: return "%dm %.1fs" % (int(value // 60), value % 60)
    return "%.2fs" % value


def _number(value, digits=2):
    return "—" if value is None else ("%.*f" % (digits, value))


def _money(value):
    return "—" if value is None else "$%.4f" % value


class StatisticsDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent); self.store = store
        self.setWindowTitle("BiblioSleuth AI statistics"); self.resize(1050, 760)
        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.period = QComboBox(); self.period.addItems(["Session", "7 days", "30 days", "90 days", "All"])
        self.model = QComboBox(); self.preset = QComboBox(); self.source = QComboBox(); self.source.addItems(["All", "Live", "Cache"])
        self.outcome = QComboBox(); self.outcome.addItems(["All", "ready", "applied", "skipped", "discarded", "failed", "cancelled"])
        for label, widget in (("Period", self.period), ("Model", self.model), ("Preset", self.preset), ("Source", self.source), ("Outcome", self.outcome)):
            filters.addWidget(QLabel(label)); filters.addWidget(widget)
        filters.addStretch(1); layout.addLayout(filters)
        self.tabs = QTabWidget(); layout.addWidget(self.tabs)
        self.overview = QTextBrowser(); self.tabs.addTab(self.overview, "Overview")
        comparison = QWidget(); comparison_layout = QVBoxLayout(comparison); group_row = QHBoxLayout()
        group_row.addWidget(QLabel("Group by")); self.group_by = QComboBox()
        self.group_by.addItem("Optimization preset", "preset"); self.group_by.addItem("Model", "model")
        self.group_by.addItem("Live vs cache", "source"); self.group_by.addItem("Outcome", "outcome")
        self.group_by.addItem("Date", "date"); self.group_by.addItem("Single vs batch", "batch_type")
        group_row.addWidget(self.group_by); group_row.addStretch(1); comparison_layout.addLayout(group_row)
        self.comparison = QTableWidget(); self.comparison.setColumnCount(7)
        self.comparison.setHorizontalHeaderLabels(["Group", "Books", "Median", "P90", "Success", "Avg. tokens", "Avg. cost"])
        self.comparison.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        comparison_layout.addWidget(self.comparison); self.tabs.addTab(comparison, "Comparisons")
        note = QLabel("History contains anonymized metrics only—never titles, paths, EPUB text, prompts, responses, evidence URLs, or API keys.")
        note.setWordWrap(True); layout.addWidget(note)
        buttons = QHBoxLayout(); export = QPushButton("Export filtered CSV…"); export.clicked.connect(self.export_csv)
        clear = QPushButton("Clear all statistics…"); clear.clicked.connect(self.clear_history)
        close = QPushButton("Close"); close.clicked.connect(self.accept)
        buttons.addWidget(export); buttons.addWidget(clear); buttons.addStretch(1); buttons.addWidget(close); layout.addLayout(buttons)
        for widget in (self.period, self.model, self.preset, self.source, self.outcome, self.group_by):
            widget.currentIndexChanged.connect(self.refresh)
        self._populate_filter_values(); self.refresh()

    def _populate_filter_values(self):
        records = self.store.records()
        self.model.blockSignals(True); self.preset.blockSignals(True)
        self.model.clear(); self.model.addItem("All")
        self.preset.clear(); self.preset.addItem("All")
        self.model.addItems(sorted({str(r.get("model")) for r in records if r.get("model")}))
        self.preset.addItems(sorted({str(r.get("preset")) for r in records if r.get("preset")}))
        self.model.blockSignals(False); self.preset.blockSignals(False)

    def _filtered(self):
        return filter_records(
            self.store.records(), self.period.currentText(), self.model.currentText(),
            self.preset.currentText(), self.source.currentText().lower(),
            self.outcome.currentText().lower(), self.store.session_id,
        )

    def refresh(self, *_):
        records = self._filtered(); data = summarize(records); timing = data["timing"]; usage = data["usage"]
        success_rate = (100.0 * data["successful"] / data["records"]) if data["records"] else None
        timing_rows = [
            ("Queue wait", timing["queue_wait_seconds"]), ("EPUB fingerprint", timing["fingerprint_seconds"]),
            ("Cache lookup", timing["cache_lookup_seconds"]), ("EPUB extraction", timing["epub_extraction_seconds"]),
            ("OpenAI request (search + reasoning + generation)", timing["openai_seconds"]),
            ("Response validation", timing["validation_seconds"]), ("Total retrieval", timing["retrieval_seconds"]),
            ("Waiting for review", timing["review_wait_seconds"]), ("Metadata normalization and application", timing["apply_seconds"]),
        ]
        rows = "".join("<tr><td>%s</td><td>%s average</td></tr>" % (html.escape(label), _duration(value)) for label, value in timing_rows)
        self.overview.setHtml(
            "<h2>Overview</h2><table cellspacing='8'>"
            "<tr><td><b>Books researched</b></td><td>%d</td><td><b>Successful</b></td><td>%d (%s%%)</td></tr>"
            "<tr><td>Failed</td><td>%d</td><td>Cancelled</td><td>%d</td></tr>"
            "<tr><td>Applied</td><td>%d</td><td>Skipped / discarded</td><td>%d / %d</td></tr>"
            "<tr><td>Live lookups</td><td>%d</td><td>Cache hits</td><td>%d</td></tr></table>"
            "<h2>Retrieval speed</h2><table cellspacing='8'>"
            "<tr><td>Total retrieval time</td><td>%s</td><td>Books per minute</td><td>%s</td></tr>"
            "<tr><td>Average</td><td>%s</td><td>Median</td><td>%s</td></tr>"
            "<tr><td>Fastest</td><td>%s</td><td>Slowest</td><td>%s</td></tr>"
            "<tr><td>P90</td><td>%s</td><td>P95</td><td>%s</td></tr></table>"
            "<h2>Average timing breakdown</h2><table cellspacing='8'>%s</table>"
            "<p><i>The API exposes only total request time; web search, reasoning, and generation cannot be separated.</i></p>"
            "<h2>Usage and estimated cost</h2><table cellspacing='8'>"
            "<tr><td>Input tokens</td><td>%d</td><td>Cached input</td><td>%d</td></tr>"
            "<tr><td>Output tokens</td><td>%d</td><td>Reasoning tokens</td><td>%d</td></tr>"
            "<tr><td>Total tokens</td><td>%d</td><td>Web searches</td><td>%d</td></tr>"
            "<tr><td>Average tokens / record</td><td>%s</td><td>Tokens / success</td><td>%s</td></tr>"
            "<tr><td>Estimated total cost</td><td>%s</td><td>Average cost / record</td><td>%s</td></tr>"
            "<tr><td>Cost / success</td><td>%s</td><td>Estimated cache savings</td><td>%s</td></tr></table>"
            "<p><i>Cost estimates use standard pricing as of %s and are not invoices.</i></p>" % (
                data["records"], data["successful"], _number(success_rate, 1), data["failed"], data["cancelled"],
                data["applied"], data["skipped"], data["discarded"], data["live"], data["cache_hits"],
                _duration(data["total_retrieval_seconds"]), _number(data["books_per_minute"]),
                _duration(data["average_seconds"]), _duration(data["median_seconds"]), _duration(data["fastest_seconds"]),
                _duration(data["slowest_seconds"]), _duration(data["p90_seconds"]), _duration(data["p95_seconds"]), rows,
                usage["input_tokens"], usage["cached_tokens"], usage["output_tokens"], usage["reasoning_tokens"],
                usage["total_tokens"], usage["web_search_calls"], _number(data["average_tokens"], 0),
                _number(data["tokens_per_success"], 0), _money(usage["estimated_cost_usd"]),
                _money(data["average_cost"]), _money(data["cost_per_success"]),
                _money(usage["estimated_avoided_cost_usd"]), html.escape(PRICING_AS_OF),
            )
        )
        groups = group_summaries(records, self.group_by.currentData()); self.comparison.setRowCount(len(groups))
        for row, (name, summary) in enumerate(groups):
            success = (100.0 * summary["successful"] / summary["records"]) if summary["records"] else 0
            values = (name, summary["records"], _duration(summary["median_seconds"]), _duration(summary["p90_seconds"]),
                      "%.1f%%" % success, _number(summary["average_tokens"], 0), _money(summary["average_cost"]))
            for column, value in enumerate(values): self.comparison.setItem(row, column, QTableWidgetItem(str(value)))

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export anonymized BiblioSleuth AI statistics", "bibliosleuth-ai-statistics.csv", "CSV files (*.csv)")
        if path:
            self.store.export_csv(path, self._filtered()); QMessageBox.information(self, "Statistics exported", "Exported anonymized statistics to:\n%s" % path)

    def clear_history(self):
        if QMessageBox.question(self, "Clear all statistics?", "Permanently delete all locally stored BiblioSleuth AI statistics?") != QMessageBox.StandardButton.Yes: return
        count = self.store.clear(); self._populate_filter_values(); self.refresh(); QMessageBox.information(self, "Statistics cleared", "Deleted %d record(s)." % count)
