import copy
import secrets
import time
import traceback
import platform
from datetime import datetime, timezone

from calibre.gui2 import FunctionDispatcher, error_dialog, info_dialog
from calibre.gui2.actions import InterfaceAction
from calibre.gui2.threaded_jobs import ThreadedJob
from calibre.ebooks.metadata import authors_to_sort_string, title_sort
from calibre.utils.date import parse_date
from calibre.constants import __version__ as CALIBRE_VERSION
from qt.core import (
    QApplication, QCheckBox, QColor, QDialog, QDialogButtonBox, QHBoxLayout, QIcon, QLabel,
    QMenu, QMessageBox, QPainter, QPlainTextEdit, QPushButton, QToolButton,
    QVBoxLayout, Qt, QTimer,
)

from .epub import epub_structural_diagnostics, extract_epub
from .docs import ApiKeySetupDialog, DocumentationDialog
from .diagnostics import diagnostic_report
from .diagnostic_bundle_dialog import DiagnosticBundleDialog
from .onboarding import SetupWizard
from .normalizer import normalize_identifiers, normalize_tags, sanitize_comments
from .lookup_cache import SESSION_LOOKUP_CACHE, epub_file_signature, epub_fingerprint, research_cache_key
from .openai_provider import OpenAIProvider
from .prefs import api_key, diagnostic_journal, effective_optimization_settings, effective_prompt, metrics_store, prefs, prompt_needs_revalidation
from .review import ReviewDialog
from .statistics_dialog import StatisticsDialog
from .metrics import summarize
from .usage import estimate_cost_usd, format_usage
from .constants import FIELD_NAMES


UNDO_STACK = []


def all_proposed_fields(result):
    """Every non-null AI field, including a separately actionable series index."""
    selected = [name for name, field in result["fields"].items() if field["value"] is not None]
    series = result["fields"].get("series", {}).get("value")
    if series is not None and series.get("index") is not None:
        selected.append("series_index")
    return selected


def redact_job_context(value, job):
    text = str(value or "")
    for key, replacement in (("title", "[REDACTED_BOOK]"), ("path", "[REDACTED_PATH]")):
        sensitive = str(job.get(key) or "")
        if sensitive: text = text.replace(sensitive, replacement)
    return text


class PendingResultsNotification(QDialog):
    """Persistent, non-modal notice for completed research awaiting review."""
    def __init__(self, action):
        super().__init__(action.gui)
        self.action = action
        self.setWindowTitle("BiblioSleuth AI results ready")
        self.setModal(False)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.resize(720, 200)
        layout = QVBoxLayout(self)
        self.message = QLabel(); self.message.setWordWrap(True); layout.addWidget(self.message)
        buttons = QHBoxLayout()
        review = QPushButton("Review books"); review.setDefault(True); review.clicked.connect(self._review)
        accept_all = QPushButton("Accept all…"); accept_all.setToolTip("Apply every non-empty proposal without field-by-field review"); accept_all.clicked.connect(self._accept_all)
        hide = QPushButton("Hide notification"); hide.clicked.connect(self.hide)
        abort = QPushButton("Abort"); abort.setToolTip("Discard all completed results waiting for review"); abort.clicked.connect(self._abort)
        buttons.addWidget(review); buttons.addWidget(accept_all); buttons.addWidget(hide); buttons.addWidget(abort); layout.addLayout(buttons)

    def update_message(self, batches, books):
        self.message.setText(
            "Research is complete. %d book(s) in %d completed job(s) are waiting for review.\n\n"
            "You can review normally, accept every proposal without reviewing, hide this notice and return later, "
            "or abort to discard all waiting results." % (books, batches)
        )

    def _review(self):
        self.hide(); self.action.review_pending_results()

    def _abort(self):
        self.hide(); self.action.discard_pending_results()

    def _accept_all(self):
        self.action.accept_all_pending_results()

    def closeEvent(self, event):
        # The title-bar close control behaves like Hide; results remain available.
        event.ignore(); self.hide()


class CompletionDialog(QDialog):
    """Resizable completion summary that cannot be clipped by Calibre's info dialog."""
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.message = message
        self.setWindowTitle("BiblioSleuth AI results")
        self.resize(760, 320)
        self.setMinimumSize(560, 260)
        layout = QVBoxLayout(self)
        title = QLabel("Metadata review complete")
        title_font = title.font(); title_font.setBold(True); title_font.setPointSize(title_font.pointSize() + 2); title.setFont(title_font)
        layout.addWidget(title)
        self.summary = QPlainTextEdit(); self.summary.setReadOnly(True); self.summary.setPlainText(message)
        self.summary.setAccessibleName("BiblioSleuth AI completion summary"); layout.addWidget(self.summary)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        copy_button = buttons.addButton("Copy summary", QDialogButtonBox.ButtonRole.ActionRole)
        copy_button.clicked.connect(lambda: QApplication.clipboard().setText(self.message))
        buttons.rejected.connect(self.reject); layout.addWidget(buttons)


class SpecificFieldsDialog(QDialog):
    LABELS = {
        "title": "Title", "authors": "Authors", "series": "Series and series index",
        "tags": "Tags", "identifiers": "Identifiers", "published_date": "Published date",
        "publisher": "Publisher", "comments": "Description",
    }

    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Research specific metadata fields"); self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        intro = QLabel("Choose the metadata to research. Only selected fields will be requested from OpenAI and shown for review. Series always includes the book's series index.")
        intro.setWordWrap(True); layout.addWidget(intro); self.checkboxes = {}
        for name in FIELD_NAMES:
            checkbox = QCheckBox(self.LABELS[name]); checkbox.setAccessibleName("Research " + self.LABELS[name])
            self.checkboxes[name] = checkbox; layout.addWidget(checkbox)
        row = QHBoxLayout(); select_all = QPushButton("Select all"); clear = QPushButton("Clear selection")
        select_all.clicked.connect(lambda: self._set_all(True)); clear.clicked.connect(lambda: self._set_all(False))
        row.addWidget(select_all); row.addWidget(clear); row.addStretch(1); layout.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        start = buttons.addButton("Start field-specific research", QDialogButtonBox.ButtonRole.AcceptRole)
        start.clicked.connect(self._accept_selection); buttons.rejected.connect(self.reject); layout.addWidget(buttons)

    def _set_all(self, checked):
        for checkbox in self.checkboxes.values(): checkbox.setChecked(checked)

    def _accept_selection(self):
        if not self.selected_fields():
            QMessageBox.information(self, "Select metadata fields", "Select at least one field to research.")
            return
        self.accept()

    def selected_fields(self):
        return tuple(name for name in FIELD_NAMES if self.checkboxes[name].isChecked())


def research_books(jobs, settings, log=None, abort=None, notifications=None):
    """Run metadata research as a native Calibre background job."""
    results = []
    total = len(jobs)
    api_secret = settings.pop("api_key")
    worker_started = time.perf_counter()
    provider = OpenAIProvider(
        api_secret, settings["model"], settings["timeout"], settings["search"],
        reasoning_effort=settings["reasoning"], max_output_tokens=settings["output_cap"],
        evidence_url_limit=settings["evidence_urls"],
    )
    usage = {key: 0 for key in ("input_tokens", "cached_tokens", "output_tokens", "reasoning_tokens", "total_tokens", "web_search_calls")}
    usage["estimated_cost_usd"] = 0.0
    cost_available = True
    api_secret = None

    def capture_usage():
        nonlocal cost_available
        detail = dict(provider.last_usage)
        if not detail:
            return {}
        detail["estimated_cost_usd"] = estimate_cost_usd(settings["model"], detail)
        for key in ("input_tokens", "cached_tokens", "output_tokens", "reasoning_tokens", "total_tokens", "web_search_calls"):
            usage[key] += detail.get(key, 0)
        if detail["estimated_cost_usd"] is None:
            cost_available = False
        else:
            usage["estimated_cost_usd"] += detail["estimated_cost_usd"]
        return detail
    try:
        for position, book in enumerate(jobs):
            if abort is not None and abort.is_set():
                if log is not None:
                    log("BiblioSleuth AI research cancelled")
                break
            book_start = float(position) / total
            book_span = 1.0 / total
            if notifications is not None:
                # Calibre treats exactly 0% as unavailable. Start just above zero,
                # then report the locally observable stages around the opaque API call.
                notifications.put((book_start + book_span * 0.02, "Reading EPUB: %s" % book["title"]))
            if log is not None:
                log("Researching metadata for book %d of %d" % (position + 1, total))
            timing = {
                "queue_wait_seconds": max(0.0, worker_started - float(settings.get("submitted_monotonic") or worker_started)),
                "fingerprint_seconds": 0.0, "cache_lookup_seconds": 0.0, "epub_extraction_seconds": 0.0,
                "openai_seconds": 0.0, "validation_seconds": 0.0,
            }
            book_started = time.perf_counter(); phase = "fingerprint"
            try:
                if notifications is not None:
                    notifications.put((book_start + book_span * 0.03, "Fingerprinting EPUB: %s" % book["title"]))
                started = time.perf_counter()
                signature = epub_file_signature(book["path"])
                if book.get("epub_fingerprint") and tuple(book.get("epub_file_signature") or ()) == signature:
                    fingerprint = book["epub_fingerprint"]
                else:
                    fingerprint = epub_fingerprint(book["path"])
                timing["fingerprint_seconds"] = time.perf_counter() - started
                book["epub_fingerprint"] = fingerprint
                book["epub_file_signature"] = signature
                cache_key = research_cache_key(fingerprint, settings)
                if notifications is not None:
                    notifications.put((book_start + book_span * 0.08, "Checking session cache: %s" % book["title"]))
                phase = "cache"; started = time.perf_counter()
                result = None if settings.get("force_refresh") else SESSION_LOOKUP_CACHE.get(cache_key)
                timing["cache_lookup_seconds"] = time.perf_counter() - started
                if result is not None:
                    detail = {key: 0 for key in usage if key != "estimated_cost_usd"}
                    detail.update({"estimated_cost_usd": 0.0, "cache_hit": True,
                                   "estimated_avoided_cost_usd": (result.get("_lookup_info") or {}).get("original_cost_usd")})
                    timing["retrieval_seconds"] = time.perf_counter() - book_started; detail["_timing"] = timing
                    results.append((book, result, None, detail))
                    if log is not None:
                        log("Book %d used the session lookup cache; no API request was made" % (position + 1))
                else:
                    phase = "extraction"; started = time.perf_counter()
                    evidence = extract_epub(book["path"], settings["front"])
                    timing["epub_extraction_seconds"] = time.perf_counter() - started
                    if notifications is not None:
                        notifications.put((book_start + book_span * 0.15, "EPUB read; starting web research: %s" % book["title"]))
                    phase = "openai"; started = time.perf_counter()
                    result = provider.research(evidence, settings["prompt"], settings.get("requested_fields"))
                    api_elapsed = time.perf_counter() - started
                    timing.update(provider.last_timings or {"openai_seconds": api_elapsed, "validation_seconds": 0.0})
                    detail = capture_usage()
                    result["_lookup_info"] = {"researched_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                                              "model": settings["model"], "original_cost_usd": detail.get("estimated_cost_usd")}
                    timing["retrieval_seconds"] = time.perf_counter() - book_started; detail["_timing"] = timing
                    SESSION_LOOKUP_CACHE.put(cache_key, result)
                    results.append((book, result, None, detail))
                    if log is not None:
                        log("Lookup usage for book %d: %s" % (position + 1, format_usage(settings["model"], detail)))
            except Exception as exc:
                detail = capture_usage()
                if phase == "openai": timing["openai_seconds"] = time.perf_counter() - started
                elif phase == "extraction": timing["epub_extraction_seconds"] = time.perf_counter() - started
                elif phase == "fingerprint": timing["fingerprint_seconds"] = time.perf_counter() - started
                timing["retrieval_seconds"] = time.perf_counter() - book_started; detail["_timing"] = timing
                detail["_diagnostic"] = {
                    "stage": phase, "message": str(exc), "traceback": traceback.format_exc(),
                    "epub_structure": epub_structural_diagnostics(book["path"]),
                }
                results.append((book, None, str(exc), detail))
                if log is not None:
                    log.error("Research failed for book %d; review the completion dialog for details" % (position + 1))
            if notifications is not None:
                notifications.put((float(position + 1) / total, "Research complete: %s" % book["title"]))
    finally:
        provider.clear_api_key()
    if log is not None:
        if not cost_available:
            usage["estimated_cost_usd"] = None
        log("Total usage: " + format_usage(settings["model"], usage))
    elif not cost_available:
        usage["estimated_cost_usd"] = None
    usage["job_elapsed_seconds"] = time.perf_counter() - worker_started
    usage["books_completed"] = len(results)
    return {"results": results, "cancelled": abort is not None and abort.is_set(), "cancelled_count": max(0, total - len(results)), "usage": usage, "model": settings["model"],
            "metrics_context": {key: settings.get(key) for key in ("preset", "search", "reasoning", "front", "output_cap", "evidence_urls")},
            "batch_size": total}


class BiblioSleuthAIAction(InterfaceAction):
    name = "BiblioSleuth AI"
    action_spec = ("BiblioSleuth AI", None, "AI-powered exact-edition EPUB metadata matching", None)

    def genesis(self):
        self.default_icon = get_icons("images/icon.png", plugin_name="BiblioSleuth AI")  # noqa: F821 -- injected by Calibre
        self.qaction.setIcon(self.default_icon)
        self.qaction.triggered.connect(self.activate)
        self.pending_batches = []
        self.pending_notification = PendingResultsNotification(self)
        self.menu = QMenu(self.gui)
        self.configure_action = self.menu.addAction("Configure BiblioSleuth AI")
        self.configure_action.triggered.connect(self.configure)
        self.about_action = self.menu.addAction("About")
        self.about_action.triggered.connect(self.show_about)
        self.documentation_action = self.menu.addAction("Documentation")
        self.documentation_action.triggered.connect(self.show_documentation)
        self.setup_action = self.menu.addAction("Run Setup Wizard")
        self.setup_action.triggered.connect(self.run_setup_wizard)
        self.menu.addSeparator()
        self.specific_fields_action = self.menu.addAction("Research Specific Fields…")
        self.specific_fields_action.triggered.connect(self.start_specific_fields)
        self.fresh_research_action = self.menu.addAction("Research Fresh (Ignore Cache)")
        self.fresh_research_action.triggered.connect(lambda *_: self.start(force_refresh=True))
        self.accept_all_action = self.menu.addAction("Accept All Pending Results…")
        self.accept_all_action.setEnabled(False)
        self.accept_all_action.triggered.connect(self.accept_all_pending_results)
        self.clear_cache_action = self.menu.addAction("Clear Session Lookup Cache")
        self.clear_cache_action.triggered.connect(self.clear_lookup_cache)
        self.undo_action = self.menu.addAction("Undo Last BiblioSleuth AI Changes")
        self.undo_action.triggered.connect(self.undo_last)
        self.diagnostics_action = self.menu.addAction("Copy Redacted Diagnostics")
        self.diagnostics_action.triggered.connect(self.copy_diagnostics)
        self.statistics_action = self.menu.addAction("Statistics…")
        self.statistics_action.triggered.connect(self.show_statistics)
        self.collect_logs_action = self.menu.addAction("Collect Recent Diagnostic Logs…")
        self.collect_logs_action.triggered.connect(self.collect_diagnostic_logs)
        self.qaction.setMenu(self.menu)
        # ThreadedJob invokes its callback from a worker thread. FunctionDispatcher
        # queues it onto Calibre's GUI thread before any Qt widgets are created.
        self.job_finished_dispatcher = FunctionDispatcher(self._job_finished, parent=self.gui)

    def activate(self, *args):
        if self.pending_batches:
            self.review_pending_results()
        else:
            self.start()

    def start_specific_fields(self, *args):
        dialog = SpecificFieldsDialog(self.gui)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.start(requested_fields=dialog.selected_fields())

    def _pending_book_count(self):
        return sum(len(payload.get("results", [])) for payload in self.pending_batches)

    def _update_pending_icon(self):
        count = self._pending_book_count()
        if hasattr(self, "accept_all_action"):
            self.accept_all_action.setEnabled(bool(count))
        if not count:
            self.qaction.setIcon(self.default_icon)
            self.qaction.setToolTip("AI-powered exact-edition EPUB metadata matching")
            return
        pixmap = self.default_icon.pixmap(64, 64)
        painter = QPainter(pixmap); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor("#d93025")); painter.drawEllipse(38, 0, 26, 26)
        painter.setPen(QColor("white")); font = painter.font(); font.setBold(True); font.setPixelSize(16); painter.setFont(font)
        painter.drawText(38, 0, 26, 26, Qt.AlignmentFlag.AlignCenter, str(min(count, 99))); painter.end()
        self.qaction.setIcon(QIcon(pixmap))
        self.qaction.setToolTip("BiblioSleuth AI — %d book(s) ready to review" % count)

    def _show_pending_notification(self):
        count = self._pending_book_count()
        if not count: return
        self.pending_notification.update_message(len(self.pending_batches), count)
        self.pending_notification.show()

    def discard_pending_results(self):
        count = self._pending_book_count()
        for payload in self.pending_batches:
            for job, *_ in payload.get("results", []): self._update_metric(job, outcome="discarded")
        self.pending_batches.clear(); self._update_pending_icon()
        self.gui.status_bar.show_message("Discarded BiblioSleuth AI results for %d book(s)." % count, 5000)

    def accept_all_pending_results(self, *args):
        if not self.pending_batches:
            return info_dialog(self.gui, "BiblioSleuth AI", "There are no completed results waiting to accept.", show=True)
        proposals = []; review_started = time.perf_counter()
        low_confidence_fields = 0
        inferred_fields = 0
        for payload in self.pending_batches:
            for job, result, error, lookup_usage in payload.get("results", []):
                ready = job.get("_metrics_ready_monotonic")
                if ready is not None: self._update_metric(job, review_wait_seconds=max(0.0, review_started - ready))
                if error or not result:
                    continue
                selected = all_proposed_fields(result)
                for name, field in result["fields"].items():
                    if field["value"] is not None:
                        if field["confidence"] == "low": low_confidence_fields += 1
                        if field["inferred"]: inferred_fields += 1
                if selected: proposals.append((job, result, selected))
        warning = (
            "Apply every non-empty AI proposal to %d book(s) without reviewing individual fields?\n\n"
            "This includes %d inferred and %d low-confidence field(s). AI results can be wrong. "
            "A single session undo checkpoint will be created."
        ) % (len(proposals), inferred_fields, low_confidence_fields)
        if not proposals or QMessageBox.warning(
                self.gui, "Accept all pending results?", warning,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel) != QMessageBox.StandardButton.Yes:
            return
        payloads = self.pending_batches[:]
        self.pending_batches.clear(); self.pending_notification.hide(); self._update_pending_icon()
        db = self.gui.current_db.new_api; applied_ids = []; undo = []; failures = []
        for job, result, selected in proposals:
            try:
                current = db.get_metadata(job["book_id"])
                current_path = db.format(job["book_id"], "EPUB", as_path=True)
                if current.uuid != job.get("book_uuid") or epub_fingerprint(current_path) != job.get("epub_fingerprint"):
                    failures.append("%s: the Calibre record or EPUB changed while research was running" % job["title"])
                    self._record_apply_failure(job, "The Calibre record or EPUB changed", "library_changed")
                    self._update_metric(job, outcome="failed", failure_category="library_changed"); continue
                snapshot = current.deepcopy()
                apply_started = time.perf_counter()
                self._apply(db, job["book_id"], result, selected)
                self._update_metric(job, outcome="applied", apply_seconds=time.perf_counter() - apply_started)
                undo.append((job["book_id"], snapshot.uuid, snapshot)); applied_ids.append(job["book_id"])
            except Exception as exc:
                failures.append("%s: %s" % (job["title"], self._friendly_error(exc)))
                self._record_apply_failure(job, exc, "apply", traceback.format_exc())
                self._update_metric(job, outcome="failed", failure_category="apply")
        if undo: UNDO_STACK.append(undo); del UNDO_STACK[:-10]
        if applied_ids: self.gui.library_view.model().refresh_ids(applied_ids)
        usage = self._combined_usage(payloads)
        models = {payload.get("model", "unknown") for payload in payloads}
        model = next(iter(models)) if len(models) == 1 else "multiple models"
        message = "Blind accept updated %d book(s)." % len(applied_ids)
        if usage.get("total_tokens"): message += "\n\nOpenAI job usage: " + format_usage(model, usage) + "."
        if usage.get("job_elapsed_seconds") is not None:
            message += "\n\nBackground retrieval time: %.2f seconds for %d completed book(s)." % (
                usage["job_elapsed_seconds"], usage.get("books_completed", len(proposals)))
        if failures: message += "\n\nFailures:\n" + "\n".join(failures)
        CompletionDialog(message, self.gui).exec()

    @staticmethod
    def _combined_usage(payloads):
        keys = ("input_tokens", "cached_tokens", "output_tokens", "reasoning_tokens", "total_tokens", "web_search_calls", "books_completed")
        combined = {key: 0 for key in keys}; combined["estimated_cost_usd"] = 0.0
        cost_known = True
        for payload in payloads:
            usage = payload.get("usage") or {}
            for key in keys: combined[key] += usage.get(key, 0) or 0
            cost = usage.get("estimated_cost_usd")
            if cost is None: cost_known = False
            else: combined["estimated_cost_usd"] += cost
        if not cost_known: combined["estimated_cost_usd"] = None
        combined["job_elapsed_seconds"] = sum((payload.get("usage") or {}).get("job_elapsed_seconds", 0) or 0 for payload in payloads)
        return combined

    def review_pending_results(self):
        if not self.pending_batches:
            return info_dialog(self.gui, "BiblioSleuth AI", "There are no completed results waiting for review.", show=True)
        self.pending_notification.hide(); payload = self.pending_batches.pop(0); self._update_pending_icon()
        QTimer.singleShot(0, lambda: self._review_payload(payload))

    def _review_payload(self, payload):
        now = time.perf_counter()
        for job, *_ in payload.get("results", []):
            ready = job.get("_metrics_ready_monotonic")
            if ready is not None: self._update_metric(job, review_wait_seconds=max(0.0, now - ready))
        self._finished(payload["results"], payload.get("cancelled", False), payload.get("usage", {}), payload.get("model", "unknown"))
        if self.pending_batches: self._show_pending_notification()

    def initialization_complete(self):
        # Toolbar widgets do not exist during genesis. MenuButtonPopup gives the
        # action a separate arrow while preserving the main button's trigger.
        for bar in self.gui.bars_manager.bars:
            button = bar.widgetForAction(self.qaction)
            if button is not None:
                button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
                button.update()

    def configure(self, *args):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def show_documentation(self, *args):
        DocumentationDialog(self.gui).exec()

    def show_about(self, *args):
        version = ".".join(str(part) for part in self.interface_action_base_plugin.version)
        QMessageBox.about(
            self.gui,
            "About BiblioSleuth AI",
            "<h2>BiblioSleuth AI %s</h2>"
            "<p>AI-powered exact-edition EPUB metadata research for Calibre.</p>"
            "<p>Created by Terry Trent. Released under the MIT License.</p>"
            "<p>BiblioSleuth AI searches online sources, presents evidence-backed suggestions "
            "for review, and changes only the fields you approve. It does not modify the EPUB file.</p>"
            "<p>OpenAI API usage may incur charges.</p>" % version,
        )

    def clear_lookup_cache(self, *args):
        count = SESSION_LOOKUP_CACHE.clear()
        info_dialog(self.gui, "BiblioSleuth AI", "Cleared %d cached lookup(s)." % count, show=True)

    def run_setup_wizard(self, *args):
        SetupWizard(self.gui).exec()

    def copy_diagnostics(self, *args):
        version = ".".join(map(str, self.interface_action_base_plugin.version))
        QApplication.clipboard().setText(diagnostic_report(prefs, version, len(SESSION_LOOKUP_CACHE), len(metrics_store.records())))
        info_dialog(self.gui, "BiblioSleuth AI", "A redacted diagnostic report was copied to the clipboard.", show=True)

    def show_statistics(self, *args):
        StatisticsDialog(metrics_store, self.gui).exec()

    def collect_diagnostic_logs(self, *args):
        DiagnosticBundleDialog(diagnostic_journal, self._diagnostic_context(), self.gui).exec()

    def _diagnostic_context(self):
        version = ".".join(map(str, self.interface_action_base_plugin.version))
        return {
            "plugin_version": version, "calibre_version": CALIBRE_VERSION,
            "python_version": platform.python_version(), "operating_system": "%s %s" % (platform.system(), platform.release()),
            "architecture": platform.machine(),
            "redacted_configuration": diagnostic_report(prefs, version, len(SESSION_LOOKUP_CACHE), len(metrics_store.records())),
            "aggregate_statistics": summarize(metrics_store.records()),
            "diagnostic_journal_entries": len(diagnostic_journal.entries()),
        }

    def undo_last(self, *args):
        if not UNDO_STACK:
            return info_dialog(self.gui, "BiblioSleuth AI", "There are no changes to undo in this Calibre session.", show=True)
        batch = UNDO_STACK.pop(); db = self.gui.current_db.new_api; restored = []
        for book_id, book_uuid, metadata in batch:
            try:
                if db.get_metadata(book_id).uuid == book_uuid:
                    db.set_metadata(book_id, metadata, force_changes=True); restored.append(book_id)
            except Exception:
                pass
        self.gui.library_view.model().refresh_ids(restored)
        info_dialog(self.gui, "BiblioSleuth AI", "Restored metadata for %d book(s)." % len(restored), show=True)

    def start(self, force_refresh=False, requested_fields=None):
        if not prefs.get("onboarding_complete", False):
            if SetupWizard(self.gui).exec() != SetupWizard.DialogCode.Accepted:
                return
        if prompt_needs_revalidation():
            return error_dialog(self.gui, "Prompt validation required", "The custom prompt must be revalidated because the response contract changed.", show=True)
        if not api_key():
            choice = ApiKeySetupDialog.choose(self.gui)
            if choice == ApiKeySetupDialog.DOCUMENTATION:
                DocumentationDialog(self.gui).exec()
                return
            if choice != ApiKeySetupDialog.CONFIGURE:
                return
            self.interface_action_base_plugin.do_user_config(self.gui)
            if not api_key():
                return
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            return info_dialog(self.gui, "BiblioSleuth AI", "Select one or more books first.", show=True)
        db = self.gui.current_db.new_api
        jobs = []
        for index in rows:
            book_id = self.gui.library_view.model().id(index.row())
            if not db.has_format(book_id, "EPUB"):
                continue
            mi = db.get_metadata(book_id)
            jobs.append({
                "book_id": book_id, "book_uuid": mi.uuid,
                "path": db.format(book_id, "EPUB", as_path=True),
                "title": mi.title, "current": self._current(mi),
            })
        if not jobs:
            return info_dialog(self.gui, "BiblioSleuth AI", "None of the selected books contains an EPUB.", show=True)
        settings = self._settings(force_refresh=force_refresh, requested_fields=requested_fields)
        for book in jobs: book["requested_fields"] = list(settings["requested_fields"])
        missing = len(rows) - len(jobs)
        if len(rows) > 1 or missing:
            preset = prefs["optimization_preset"].title(); ranges = {"economy":"$0.01–$0.03", "balanced":"$0.01–$0.05", "thorough":"$0.02–$0.10"}
            field_text = ", ".join(SpecificFieldsDialog.LABELS[name] for name in settings["requested_fields"])
            cache_text = "Bypassed (fresh research requested)" if force_refresh else "Checked in the background job"
            text = ("Ready to research %d EPUB(s).\n\nFields: %s\nPreset: %s\nSession cache: %s\nSelected books without EPUB: %d\n"
                    "Planning estimate: %s per uncached book (not a quote).\n\nStart the background job?") % (
                        len(jobs), field_text, preset, cache_text, missing, ranges.get(prefs["optimization_preset"], "varies"))
            if QMessageBox.question(self.gui, "BiblioSleuth AI preflight", text) != QMessageBox.StandardButton.Yes: return
        self._launch_jobs(jobs, settings)

    def _launch_jobs(self, jobs, settings):
        settings = dict(settings); settings["submitted_monotonic"] = time.perf_counter()
        requested = settings.get("requested_fields") or FIELD_NAMES
        description = "Research %d metadata field(s) for %d EPUB(s)" % (len(requested), len(jobs))
        job = ThreadedJob(
            "BiblioSleuth AI research",
            description,
            research_books,
            (jobs, settings),
            {},
            self.job_finished_dispatcher,
            killable=True,
        )
        self.gui.job_manager.run_threaded_job(job)
        self.gui.status_bar.show_message(
            "BiblioSleuth AI research started. Monitor it in the Jobs panel.", 5000
        )

    def _current(self, mi):
        return {"title": mi.title, "authors": list(mi.authors or []), "series": {"name": mi.series, "index": mi.series_index} if mi.series else None,
                "tags": list(mi.tags or []), "identifiers": [{"type": k, "value": v} for k, v in mi.get_identifiers().items()],
                "published_date": mi.pubdate.isoformat() if mi.pubdate else None, "publisher": mi.publisher, "comments": mi.comments}

    def _job_finished(self, job):
        if job.failed:
            diagnostic_journal.add({
                "outcome": "failed", "stage": "background_job", "model": prefs["model"],
                "preset": prefs["optimization_preset"], "batch_size": 0, "failed_books": 1,
                "failures": [{"category": "background_job", "stage": "background_job",
                              "message": "The Calibre background job failed before returning a sanitized result.", "traceback": ""}],
            })
            box = QMessageBox(self.gui); box.setWindowTitle("BiblioSleuth AI research failed"); box.setIcon(QMessageBox.Icon.Critical)
            box.setText("The background metadata research job failed. A sanitized diagnostic entry was retained locally for seven days.")
            collect = box.addButton("Collect diagnostic logs…", QMessageBox.ButtonRole.ActionRole)
            box.addButton(QMessageBox.StandardButton.Close); box.exec()
            if box.clickedButton() is collect: self.collect_diagnostic_logs()
            return
        payload = job.result or {"results": [], "cancelled": False, "usage": {}, "model": "unknown"}
        self._record_payload_metrics(payload)
        self.pending_batches.append(payload); self._update_pending_icon(); self._show_pending_notification()
        self.gui.status_bar.show_message("BiblioSleuth AI research complete — click the notification or toolbar icon to review.", 10000)

    def _record_payload_metrics(self, payload):
        with metrics_store.batch():
            self._record_payload_metrics_unbatched(payload)

    def _record_payload_metrics_unbatched(self, payload):
        context = payload.get("metrics_context") or {}; batch_size = int(payload.get("batch_size") or len(payload.get("results", [])) or 1)
        diagnostic_failures = []; successful = 0
        for job, result, error, detail in payload.get("results", []):
            timing = dict((detail or {}).get("_timing") or {})
            record = {
                "model": payload.get("model", "unknown"), "preset": context.get("preset", "unknown"),
                "search_context": context.get("search"), "reasoning": context.get("reasoning"),
                "front_matter_chars": context.get("front"), "output_cap": context.get("output_cap"),
                "evidence_urls": context.get("evidence_urls"), "cache_hit": bool((detail or {}).get("cache_hit")),
                "outcome": "failed" if error else ("cancelled" if payload.get("cancelled") and not result else "ready"),
                "failure_category": self._failure_category(error) if error else "", "batch_size": batch_size,
            }
            record.update(timing)
            for key in ("input_tokens", "cached_tokens", "output_tokens", "reasoning_tokens", "total_tokens", "web_search_calls",
                        "estimated_cost_usd", "estimated_avoided_cost_usd"):
                record[key] = (detail or {}).get(key)
            fingerprint = job.get("epub_fingerprint") or secrets.token_hex(32)
            job["_metrics_id"] = metrics_store.add(fingerprint, record)
            job["_metrics_ready_monotonic"] = time.perf_counter()
            if error:
                diagnostic = dict((detail or {}).get("_diagnostic") or {})
                safe_message = redact_job_context(diagnostic.get("message", error), job)
                safe_trace = redact_job_context(diagnostic.get("traceback", ""), job)
                diagnostic_failures.append({
                    "anonymous_book": metrics_store.anonymized_book_id(fingerprint),
                    "category": self._failure_category(error), "stage": diagnostic.get("stage", "research"),
                    "message": safe_message, "traceback": safe_trace,
                    "epub_structure": diagnostic.get("epub_structure") or {},
                })
            else: successful += 1
        for _ in range(int(payload.get("cancelled_count") or 0)):
            metrics_store.add(secrets.token_hex(32), {
                "model": payload.get("model", "unknown"), "preset": context.get("preset", "unknown"),
                "search_context": context.get("search"), "reasoning": context.get("reasoning"),
                "front_matter_chars": context.get("front"), "output_cap": context.get("output_cap"),
                "evidence_urls": context.get("evidence_urls"), "cache_hit": False, "outcome": "cancelled",
                "failure_category": "user_cancelled", "batch_size": batch_size,
            })
        usage = dict(payload.get("usage") or {})
        diagnostic_journal.add({
            "outcome": "failed" if diagnostic_failures else ("cancelled" if payload.get("cancelled") else "success"),
            "stage": "research", "model": payload.get("model", "unknown"), "preset": context.get("preset", "unknown"),
            "batch_size": batch_size, "successful_books": successful, "failed_books": len(diagnostic_failures),
            "cancelled_books": int(payload.get("cancelled_count") or 0),
            "usage": {key: usage.get(key) for key in ("input_tokens", "cached_tokens", "output_tokens", "reasoning_tokens", "total_tokens", "web_search_calls", "estimated_cost_usd")},
            "timing": {"job_elapsed_seconds": usage.get("job_elapsed_seconds")}, "failures": diagnostic_failures,
        })

    @staticmethod
    def _failure_category(error):
        value = str(error or "").lower()
        if "epub" in value or "container.xml" in value or "opf" in value or "zip" in value: return "epub"
        if "429" in value or "rate" in value: return "rate_limit"
        if "timeout" in value or "timed out" in value: return "timeout"
        if "401" in value or "403" in value or "api key" in value: return "authentication"
        if "model" in value: return "model"
        if "schema" in value or "structured" in value or "validation" in value: return "validation"
        return "other"

    @staticmethod
    def _update_metric(job, **changes):
        record_id = job.get("_metrics_id")
        if record_id: metrics_store.update(record_id, **changes)

    def _record_apply_failure(self, job, message, category, trace=""):
        fingerprint = job.get("epub_fingerprint") or secrets.token_hex(32)
        safe_message = redact_job_context(message, job); safe_trace = redact_job_context(trace, job)
        diagnostic_journal.add({
            "outcome": "failed", "stage": "metadata_application", "model": prefs["model"],
            "preset": prefs["optimization_preset"], "batch_size": 1, "failed_books": 1,
            "failures": [{
                "anonymous_book": metrics_store.anonymized_book_id(fingerprint), "category": category,
                "stage": "metadata_application", "message": safe_message, "traceback": safe_trace,
                "epub_structure": epub_structural_diagnostics(job["path"]),
            }],
        })

    def _finished(self, results, cancelled=False, usage=None, model="unknown"):
        db = self.gui.current_db.new_api; applied = 0; failures = []; failed_jobs = []; ready = []
        for job, result, error, lookup_usage in results:
            if error:
                failures.append("%s: %s" % (job["title"], self._friendly_error(error))); failed_jobs.append(job); continue
            try:
                current_mi = db.get_metadata(job["book_id"])
                current_path = db.format(job["book_id"], "EPUB", as_path=True)
                if current_mi.uuid != job.get("book_uuid") or epub_fingerprint(current_path) != job.get("epub_fingerprint"):
                    failures.append("%s: the Calibre record or EPUB changed while research was running" % job["title"])
                    self._record_apply_failure(job, "The Calibre record or EPUB changed", "library_changed")
                    self._update_metric(job, outcome="failed", failure_category="library_changed")
                    continue
            except Exception:
                failures.append("%s: the Calibre record or EPUB is no longer available" % job["title"])
                self._record_apply_failure(job, "The Calibre record or EPUB is no longer available", "library_missing")
                self._update_metric(job, outcome="failed", failure_category="library_missing")
                continue
            ready.append((job, result, lookup_usage))
        decisions = {}; position = 0; bulk_confirmed = False
        while 0 <= position < len(ready):
            job, result, lookup_usage = ready[position]
            prior = decisions.get(position)
            dialog = ReviewDialog(job["title"], job["current"], prior[0] if prior else result, self.gui,
                                  usage=lookup_usage, model=model, batch_position=position + 1,
                                  batch_total=len(ready), selected=prior[1] if prior else None)
            outcome = dialog.exec()
            if outcome == ReviewDialog.PREVIOUS:
                position = max(0, position - 1); continue
            if outcome == ReviewDialog.FRESH:
                self._update_metric(job, outcome="discarded")
                fresh = self._settings(force_refresh=True, requested_fields=job.get("requested_fields")); self._launch_jobs([job], fresh); decisions.pop(position, None); position += 1; continue
            if outcome == ReviewDialog.ACCEPT_REMAINING:
                remaining = []
                inferred_fields = low_confidence_fields = 0
                for index in range(position, len(ready)):
                    remaining_job, remaining_result, _ = ready[index]
                    candidate = dialog.result_data if index == position else (decisions.get(index) or (remaining_result, None))[0]
                    for field in candidate["fields"].values():
                        if field["value"] is not None:
                            inferred_fields += int(bool(field["inferred"]))
                            low_confidence_fields += int(field["confidence"] == "low")
                    remaining.append((index, candidate, all_proposed_fields(candidate)))
                warning = (
                    "Accept every non-empty proposal for this book and the %d remaining book(s) without further review?\n\n"
                    "This includes %d inferred and %d low-confidence field(s). AI results can be wrong. "
                    "One session undo checkpoint will be created."
                ) % (max(0, len(remaining) - 1), inferred_fields, low_confidence_fields)
                if QMessageBox.warning(
                        self.gui, "Accept all remaining books?", warning,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                        QMessageBox.StandardButton.Cancel) != QMessageBox.StandardButton.Yes:
                    continue
                for index, candidate, selected in remaining:
                    decisions[index] = (copy.deepcopy(candidate), selected)
                bulk_confirmed = True; position = len(ready); continue
            if outcome == ReviewDialog.APPLY_NEXT:
                decisions[position] = (copy.deepcopy(dialog.result_data), dialog.selected_fields())
            else:
                decisions.pop(position, None)
            position += 1
        chosen = [(ready[i][0], value[0], value[1]) for i, value in decisions.items() if value[1]]
        applied_metric_ids = set()
        if chosen:
            summary = "Apply the reviewed metadata to %d book(s)?\n\nThis creates a session undo point." % len(chosen)
            if bulk_confirmed or QMessageBox.question(self.gui, "Confirm metadata changes", summary) == QMessageBox.StandardButton.Yes:
                undo = []
                for job, result, selected in chosen:
                    try:
                        # Use Calibre's supported clone operation. Generic
                        # copy.deepcopy() bypasses Metadata's internal invariants
                        # and can produce an object with no _data attribute.
                        current = db.get_metadata(job["book_id"])
                        old = current.deepcopy(); undo.append((job["book_id"], old.uuid, old))
                        apply_started = time.perf_counter(); self._apply(db, job["book_id"], result, selected); applied += 1
                        self._update_metric(job, outcome="applied", apply_seconds=time.perf_counter() - apply_started)
                        applied_metric_ids.add(job.get("_metrics_id"))
                    except Exception as exc:
                        failures.append("%s: %s" % (job["title"], exc)); self._record_apply_failure(job, exc, "apply", traceback.format_exc()); self._update_metric(job, outcome="failed", failure_category="apply")
                if undo: UNDO_STACK.append(undo); del UNDO_STACK[:-10]
        for job, _result, _lookup_usage in ready:
            if job.get("_metrics_id") not in applied_metric_ids and job.get("_metrics_id"):
                # Preserve explicit failure/discard outcomes; update() has no read
                # dependency, so only remaining reviewed proposals become skipped.
                current_record = metrics_store.get(job.get("_metrics_id"))
                if current_record and current_record.get("outcome") == "ready": self._update_metric(job, outcome="skipped")
        self.gui.library_view.model().refresh_ids([j[0]["book_id"] for j in results])
        message = "Updated %d book(s)." % applied
        if usage and usage.get("total_tokens"):
            message += "\n\nOpenAI job usage: " + format_usage(model, usage) + "."
        if usage and usage.get("job_elapsed_seconds") is not None:
            message += "\n\nBackground retrieval time: %.2f seconds for %d completed book(s)." % (
                usage["job_elapsed_seconds"], usage.get("books_completed", len(results)))
        if cancelled:
            message += "\n\nThe job was cancelled; completed results were retained for review."
        if failures: message += "\n\nFailures:\n" + "\n".join(failures)
        if failures:
            box = QMessageBox(self.gui); box.setWindowTitle("BiblioSleuth AI results"); box.setIcon(QMessageBox.Icon.Warning)
            box.setText(message); configure = box.addButton("Configure…", QMessageBox.ButtonRole.ActionRole)
            retry = box.addButton("Retry failed fresh", QMessageBox.ButtonRole.ActionRole); retry.setEnabled(bool(failed_jobs))
            collect = box.addButton("Collect diagnostic logs…", QMessageBox.ButtonRole.ActionRole)
            docs = box.addButton("Troubleshooting", QMessageBox.ButtonRole.HelpRole); box.addButton(QMessageBox.StandardButton.Close); box.exec()
            if box.clickedButton() is configure: self.configure()
            elif box.clickedButton() is docs: self.show_documentation()
            elif box.clickedButton() is retry:
                fields = failed_jobs[0].get("requested_fields") if failed_jobs else None
                self._launch_jobs(failed_jobs, self._settings(force_refresh=True, requested_fields=fields))
            elif box.clickedButton() is collect: self.collect_diagnostic_logs()
        else:
            CompletionDialog(message, self.gui).exec()

    @staticmethod
    def _friendly_error(error):
        value = str(error); lowered = value.lower()
        if "401" in value or "403" in value or "api key" in lowered: return "OpenAI access was rejected. Check the API key, project permissions, and billing."
        if "429" in value or "rate" in lowered: return "OpenAI rate or spending limit reached. Wait, check project limits, then retry."
        if "timeout" in lowered or "timed out" in lowered: return "The lookup timed out. Retry fresh or increase the timeout in General settings."
        if "model" in lowered: return "The selected model may be unavailable or lack required capabilities. Test it in General settings."
        if "epub" in lowered or "zip" in lowered: return "The EPUB could not be safely read. Verify the file is valid and DRM-free."
        return value.splitlines()[0]

    def _settings(self, force_refresh=False, requested_fields=None):
        optimization = effective_optimization_settings()
        return {"api_key": api_key(), "model": prefs["model"], "timeout": prefs["timeout"],
                "search": optimization["search_context_size"], "front": optimization["front_matter_chars"],
                "reasoning": optimization["reasoning_effort"], "output_cap": optimization["max_output_tokens"],
                "evidence_urls": optimization["evidence_url_limit"], "prompt": effective_prompt(), "preset": prefs["optimization_preset"],
                "requested_fields": list(requested_fields or FIELD_NAMES), "force_refresh": bool(force_refresh)}

    def _apply(self, db, book_id, result, selected):
        mi = db.get_metadata(book_id); fields = result["fields"]
        if "title" in selected:
            mi.title = fields["title"]["value"]
            language = (mi.languages or [None])[0]
            mi.title_sort = title_sort(mi.title, lang=language)
        if "authors" in selected:
            mi.authors = fields["authors"]["value"]
            mi.author_sort = authors_to_sort_string(mi.authors)
        if "series" in selected:
            value = fields["series"]["value"]; mi.series = value["name"] if value else None
            if value is None:
                mi.series_index = None
        if "series_index" in selected:
            value = fields["series"]["value"]; mi.series_index = value.get("index") if value else None
        if "tags" in selected: mi.tags = normalize_tags(fields["tags"]["value"], prefs["tag_limit"])
        if "identifiers" in selected:
            ids = mi.get_identifiers(); ids.update(normalize_identifiers(fields["identifiers"]["value"])); mi.set_identifiers(ids)
        if "published_date" in selected: mi.pubdate = parse_date(fields["published_date"]["value"], assume_utc=True)
        if "publisher" in selected: mi.publisher = fields["publisher"]["value"]
        if "comments" in selected: mi.comments = sanitize_comments(fields["comments"]["value"], prefs["description_limit"])
        db.set_metadata(book_id, mi, force_changes=True)
