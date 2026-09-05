import os

from qt.core import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QRect,
    QSize, QSizePolicy, QSpinBox, QTabWidget, QTimer, QVBoxLayout, QWidget, Qt,
)

from .constants import DEFAULT_SYSTEM_PROMPT, PLUGIN_VERSION, PROMPT_VERSION, SCHEMA_VERSION
from . import credentials
from .docs import DocumentationDialog
from .provider_base import ProviderError
from .providers import (
    create_provider, effective_reasoning, PROVIDER_LABELS, provider_spec, sanitize_anthropic_models,
    sanitize_model_list, resolve_anthropic_workspace_id, model_id_for_discovery,
)
from .provider_config import ProviderConfigurationState
from .prefs import OPTIMIZATION_PRESETS, api_key, forget_session_api_key, metrics_store, prefs, set_session_api_key, provider_requires_key
from .searxng import SearXNGClient
from .prompt_validation import PromptValidationError, validate_and_repair_prompt
from .prompt_validation import validation_matches_prompt
from .diagnostics import diagnostic_report
from .lookup_cache import SESSION_LOOKUP_CACHE
from .model_catalog import cache_is_fresh, cached_models, normalize_models, store_models
from .usage import estimate_cost_usd, format_usage
from .statistics_dialog import StatisticsDialog


class WrappedValueLabel(QLabel):
    """QLabel with a reliable multi-line height inside QFormLayout."""
    def __init__(self, text="", parent=None):
        super().__init__("", parent)
        self.setWordWrap(True)
        self.setMinimumWidth(0)
        self.setMaximumWidth(520)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def setText(self, text):
        super().setText(text)
        # QFormLayout can ignore minimumSizeHint after a hidden tab is activated.
        # An explicit minimum height is honored consistently on macOS/Calibre.
        self.setMinimumHeight(self._wrapped_height())
        self.updateGeometry()

    def _wrapped_height(self):
        # Calculate conservatively at 420px so narrower Calibre configuration
        # hosts receive enough row height instead of clipping wrapped lines.
        bounds = self.fontMetrics().boundingRect(
            QRect(0, 0, 420, 10000), Qt.TextFlag.TextWordWrap, self.text()
        )
        return max(self.fontMetrics().height(), bounds.height()) + 8

    def sizeHint(self):
        return QSize(520, self._wrapped_height())

    def minimumSizeHint(self):
        return QSize(0, self._wrapped_height())


class ConfigWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._validated = None
        self._provider_keys = {}
        self._provider_models = dict(prefs["provider_models"] or {})
        self._provider_endpoints = dict(prefs["provider_endpoints"] or {})
        initial_provider = prefs["provider"]
        self._provider_state = ProviderConfigurationState(
            initial_provider, self._provider_models, self._provider_endpoints, self._provider_keys
        )
        self._environment_key = self._environment_key_for(initial_provider)
        self._has_existing_key = bool(api_key(initial_provider))
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget(); layout.addWidget(self.tabs)
        general = QWidget(); general_layout = QVBoxLayout(general); general_form = QFormLayout()
        optimization = QWidget(); optimization_layout = QVBoxLayout(optimization); optimization_form = QFormLayout()
        prompt_tab = QWidget(); prompt_layout = QVBoxLayout(prompt_tab)
        statistics_tab = QWidget(); statistics_layout = QVBoxLayout(statistics_tab); statistics_form = QFormLayout()
        privacy_tab = QWidget(); privacy_layout = QVBoxLayout(privacy_tab)
        help_tab = QWidget(); help_layout = QVBoxLayout(help_tab)
        self.tabs.addTab(general, "General")
        self.tabs.addTab(optimization, "Optimization")
        self.tabs.addTab(prompt_tab, "System Prompt")
        self.tabs.addTab(statistics_tab, "Statistics")
        self.tabs.addTab(privacy_tab, "Privacy & Security")
        self.tabs.addTab(help_tab, "Help")
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        if self._environment_key:
            self.api_key.setPlaceholderText("Using provider environment variable")
            self.api_key.setEnabled(False)
        elif self._has_existing_key:
            self.api_key.setPlaceholderText("Stored securely — enter a new key to replace it")
        else:
            self.api_key.setPlaceholderText("sk-...")
        self.api_key_label = QLabel(self._api_key_field_label())
        self.key_status = WrappedValueLabel(self._key_status_text())
        self.remember_key = QCheckBox("Remember securely in the operating system credential vault")
        self.remember_key.setChecked(bool(prefs["remember_api_key"] and credentials.available()))
        self.remember_key.setEnabled(credentials.available() and not self._environment_key)
        self.provider = QComboBox()
        for provider_id, label in PROVIDER_LABELS.items(): self.provider.addItem(label, provider_id)
        self.provider.setCurrentIndex(max(0, self.provider.findData(initial_provider)))
        self._active_provider = initial_provider
        self.search_mode = QComboBox(); self.search_mode.addItem("Provider-hosted search", "hosted"); self.search_mode.addItem("SearXNG", "searxng")
        self.search_mode.setCurrentIndex(max(0, self.search_mode.findData(prefs["search_mode"])))
        self.endpoint = QLineEdit(self._provider_endpoints.get(initial_provider, ""))
        self.endpoint.setPlaceholderText("Local API endpoint")
        environment_workspace = resolve_anthropic_workspace_id()
        self.workspace_id = QLineEdit(resolve_anthropic_workspace_id(
            prefs["anthropic_workspace_id"]
        ))
        self.workspace_id.setPlaceholderText("Optional unless your key requires it (wrkspc_…)")
        self.workspace_id.setEnabled(not bool(environment_workspace))
        self.searxng_url = QLineEdit(prefs["searxng_url"]); self.searxng_url.setPlaceholderText("http://127.0.0.1:8080")
        self.max_searches = QSpinBox(); self.max_searches.setRange(1, 10); self.max_searches.setValue(prefs["max_searches"])
        self.searxng_results = QSpinBox(); self.searxng_results.setRange(1, 10); self.searxng_results.setValue(prefs["searxng_results"])
        self.model = QComboBox(); self.model.setEditable(False)
        initial_model = self._provider_models.get(initial_provider) or prefs["model"]
        self.model.addItems(cached_models(prefs, initial_model, provider=initial_provider))
        self.model.setCurrentText(initial_model)
        self.model_status = WrappedValueLabel(
            "Account-visible model choices are cached for seven days. Use the capability test before selecting an unfamiliar model."
        )
        self.timeout = QSpinBox(); self.timeout.setRange(10, 300); self.timeout.setValue(prefs["timeout"])
        self.preset = QComboBox(); self.preset.addItems(["Economy", "Balanced", "Thorough", "Custom"])
        self.preset.setCurrentText(prefs["optimization_preset"].title())
        self.search = QComboBox(); self.search.addItems(["low", "medium", "high"]); self.search.setCurrentText(prefs["search_context_size"])
        self.front = QSpinBox(); self.front.setRange(1000, 50000); self.front.setValue(prefs["front_matter_chars"])
        self.reasoning = QComboBox(); self.reasoning.addItems(["none", "low", "medium", "high"]); self.reasoning.setCurrentText(prefs["reasoning_effort"])
        self.output_cap = QSpinBox(); self.output_cap.setRange(800, 10000); self.output_cap.setSingleStep(100); self.output_cap.setValue(prefs["max_output_tokens"])
        self.evidence_urls = QSpinBox(); self.evidence_urls.setRange(1, 10); self.evidence_urls.setValue(prefs["evidence_url_limit"])
        self.tags = QSpinBox(); self.tags.setRange(1, 100); self.tags.setValue(prefs["tag_limit"])
        self.description = QSpinBox(); self.description.setRange(500, 30000); self.description.setValue(prefs["description_limit"])
        general_form.addRow("AI provider", self.provider)
        general_form.addRow("Web research", self.search_mode)
        general_form.addRow("Local API endpoint", self.endpoint)
        self.workspace_id_label = QLabel("Claude workspace ID")
        general_form.addRow(self.workspace_id_label, self.workspace_id)
        general_form.addRow("SearXNG server", self.searxng_url)
        general_form.addRow("Maximum searches per book", self.max_searches)
        general_form.addRow("Results per search", self.searxng_results)
        general_form.addRow(self.api_key_label, self.api_key)
        general_form.addRow("Status", self.key_status)
        general_form.addRow("", self.remember_key); general_form.addRow("Model", self.model)
        general_form.addRow("Model choices", self.model_status)
        general_form.addRow("Timeout (seconds)", self.timeout)
        general_layout.addLayout(general_form)
        general_buttons = QGridLayout()
        test = QPushButton("Test Connection"); test.clicked.connect(self.test_connection); general_buttons.addWidget(test, 0, 0)
        capabilities = QPushButton("Test Model Capabilities…"); capabilities.clicked.connect(self.test_capabilities); general_buttons.addWidget(capabilities, 0, 1)
        refresh_models = QPushButton("Refresh Model Choices"); refresh_models.clicked.connect(self.refresh_model_choices); general_buttons.addWidget(refresh_models, 1, 0, 1, 2)
        test_search = QPushButton("Test SearXNG"); test_search.clicked.connect(self.test_searxng); general_buttons.addWidget(test_search, 2, 0, 1, 2)
        self.delete_key_button = QPushButton("Delete Stored API Key"); self.delete_key_button.clicked.connect(self.forget_api_key); general_buttons.addWidget(self.delete_key_button, 3, 0, 1, 2)
        general_layout.addLayout(general_buttons); general_layout.addStretch(1)

        optimization_form.addRow("Optimization preset", self.preset)
        self.preset_description = WrappedValueLabel()
        optimization_form.addRow("Preset summary", self.preset_description)
        optimization_form.addRow("Web search context", self.search); optimization_form.addRow("Title/copyright evidence characters", self.front)
        optimization_form.addRow("Reasoning effort", self.reasoning); optimization_form.addRow("Maximum output tokens", self.output_cap)
        optimization_form.addRow("Maximum evidence URLs per field", self.evidence_urls)
        optimization_form.addRow("Maximum tags", self.tags)
        optimization_form.addRow("Maximum description characters", self.description)
        optimization_layout.addLayout(optimization_form); optimization_layout.addStretch(1)

        prompt_layout.addWidget(QLabel("System prompt override (empty uses the bundled default):"))
        self.prompt = QPlainTextEdit(prefs["system_prompt_override"])
        self.prompt.setMinimumHeight(240)
        self.prompt.textChanged.connect(self._prompt_changed)
        prompt_layout.addWidget(self.prompt)
        buttons = QGridLayout()
        for label, handler in (
            ("Validate Prompt", self.validate_prompt), ("Restore Default", self.restore_default),
            ("Preview Effective Prompt", self.preview), ("View Default Prompt", self.view_default),
            ("Copy Default", self.copy_default),
        ):
            button = QPushButton(label); button.clicked.connect(handler)
            index = buttons.count(); buttons.addWidget(button, index // 2, index % 2)
        prompt_layout.addLayout(buttons)
        self.delete_key_button.setEnabled(self._has_existing_key)
        self.status = WrappedValueLabel(self._status_text()); prompt_layout.addWidget(self.status)

        self.statistics_enabled = QCheckBox("Collect anonymized performance statistics")
        self.statistics_enabled.setChecked(bool(prefs["statistics_enabled"]))
        self.statistics_days = QSpinBox(); self.statistics_days.setRange(1, 3650); self.statistics_days.setValue(prefs["statistics_retention_days"])
        self.statistics_records = QSpinBox(); self.statistics_records.setRange(10, 100000); self.statistics_records.setValue(prefs["statistics_max_records"])
        statistics_form.addRow("Collection", self.statistics_enabled)
        statistics_form.addRow("Retention (days)", self.statistics_days)
        statistics_form.addRow("Maximum records", self.statistics_records)
        statistics_layout.addLayout(statistics_form)
        statistics_layout.addWidget(WrappedValueLabel(
            "Records contain timings, model and preset, research limits, usage, estimated cost, outcome, batch size, and a salted anonymous EPUB identifier. "
            "They never contain titles, authors, paths, library IDs, EPUB text, prompts, responses, URLs, or API keys."
        ))
        stats_buttons = QHBoxLayout(); view_stats = QPushButton("View Statistics…"); view_stats.clicked.connect(self.show_statistics)
        clear_stats = QPushButton("Clear Statistics…"); clear_stats.clicked.connect(self.clear_statistics)
        stats_buttons.addWidget(view_stats); stats_buttons.addWidget(clear_stats); stats_buttons.addStretch(1)
        statistics_layout.addLayout(stats_buttons); statistics_layout.addStretch(1)

        privacy = QLabel(
            "Only selected OPF fields and confidently identified title/copyright-page text are sent. Unidentified pages and chapters are never used as fallback evidence. EPUB and web text are untrusted evidence. "
            "Keys use the operating-system vault; generated HTML, URLs, responses, and archives are locally constrained."
        )
        self._constrain_wrapped_label(privacy); privacy_layout.addWidget(privacy)
        billing = QLabel(
            "Prompt validation/repair and metadata research are billable API calls. "
            "API keys are stored in the operating system credential vault when available, never in Calibre's JSON preferences."
        ); self._constrain_wrapped_label(billing); privacy_layout.addWidget(billing); privacy_layout.addStretch(1)

        help_text = QLabel("Open the complete guide or copy a redacted diagnostic report suitable for support requests.")
        help_text.setWordWrap(True); help_layout.addWidget(help_text)
        help_buttons = QHBoxLayout()
        docs_button = QPushButton("Documentation"); docs_button.clicked.connect(self.show_documentation); help_buttons.addWidget(docs_button)
        diagnostics_button = QPushButton("Copy Redacted Diagnostics"); diagnostics_button.clicked.connect(self.copy_diagnostics); help_buttons.addWidget(diagnostics_button)
        help_layout.addLayout(help_buttons); help_layout.addStretch(1)
        self.preset.currentTextChanged.connect(self._preset_changed)
        self.provider.currentIndexChanged.connect(self._provider_changed)
        self.search_mode.currentIndexChanged.connect(self._update_provider_controls)
        self._preset_changed(self.preset.currentText())
        self._update_provider_controls()
        if not cache_is_fresh(prefs, provider=initial_provider) and (
            self._has_existing_key or not provider_requires_key(initial_provider)
        ):
            QTimer.singleShot(0, self._refresh_models_if_stale)

    @staticmethod
    def _constrain_wrapped_label(label):
        label.setWordWrap(True)
        label.setMinimumWidth(0)
        label.setMaximumWidth(520)
        # Ignored collapses a word-wrapped QLabel's field column to zero in
        # Calibre's configuration host. Preferred honors the 520px cap without
        # forcing a horizontal scrollbar.
        label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

    @staticmethod
    def _environment_key_for(provider):
        name = provider_spec(provider).environment_variable
        return bool(name and os.environ.get(name, "").strip())

    def _provider_id(self):
        widget = getattr(self, "provider", None)
        return (widget.currentData() if widget is not None else prefs["provider"]) or "openai"

    def _provider_changed(self, *_):
        self._provider_state.capture(
            self.model.currentText(), self.endpoint.text(), self.api_key.text()
        )
        provider = self._provider_id()
        selected = self._provider_state.switch(provider)
        self._active_provider = provider
        self.api_key.clear(); self._environment_key = self._environment_key_for(provider)
        self._has_existing_key = bool(api_key(provider))
        self.api_key.setEnabled(not self._environment_key)
        self.remember_key.setEnabled(credentials.available() and not self._environment_key)
        self.api_key.setPlaceholderText("Using environment variable" if self._environment_key else ("Stored securely — enter a replacement" if self._has_existing_key else "Optional local token" if provider in ("ollama", "lmstudio") else "API key"))
        self.api_key_label.setText(self._api_key_field_label()); self.key_status.setText(self._key_status_text())
        self.delete_key_button.setEnabled(self._has_existing_key)
        target_model = selected["model"]
        self.model.blockSignals(True); self.model.clear()
        self.model.addItems(cached_models(
            prefs, target_model or provider_spec(provider).default_model, provider=provider
        ))
        self.model.setCurrentText(target_model); self.model.blockSignals(False)
        self.endpoint.setText(selected["endpoint"])
        self.status.setText(self._status_text())
        self._update_provider_controls()

    def _update_provider_controls(self, *_):
        provider = self._provider_id(); spec = provider_spec(provider)
        local = not spec.hosted_search
        self.endpoint.setVisible(local)
        anthropic = provider == "anthropic"
        self.workspace_id_label.setVisible(anthropic)
        self.workspace_id.setVisible(anthropic)
        self.search_mode.setEnabled(not local)
        if local: self.search_mode.setCurrentIndex(self.search_mode.findData("searxng"))
        uses_searxng = local or self.search_mode.currentData() == "searxng"
        for widget in (self.searxng_url, self.max_searches, self.searxng_results): widget.setEnabled(uses_searxng)
        self._update_optimization_controls()

    def _update_optimization_controls(self):
        name = self.preset.currentText().lower()
        custom = name == "custom"
        for widget in (self.front, self.search, self.output_cap, self.evidence_urls):
            widget.setEnabled(custom)
        supports_reasoning = provider_spec(self._provider_id()).reasoning
        self.reasoning.setEnabled(custom and supports_reasoning)
        if self._provider_id() == "lmstudio":
            explanation = "Reasoning is controlled by the loaded model. Use a non-thinking instruct model for reliable structured output."
        elif self._provider_id() == "ollama":
            explanation = "BiblioSleuth AI disables Ollama reasoning for reliable structured output."
        else:
            explanation = "Controls reasoning effort for supported hosted models when Custom optimization is selected."
        self.reasoning.setToolTip(explanation)
        summaries = {
            "economy": "Lowest expected cost: shorter title/copyright evidence, low search context, no reasoning, 2 evidence URLs.",
            "balanced": "Recommended: bounded title/copyright evidence, low search context and reasoning, 3 evidence URLs.",
            "thorough": "Hard editions: longer title/copyright evidence, medium search context and reasoning, 4 evidence URLs.",
            "custom": "Advanced controls are unlocked below. Higher settings can increase latency and cost.",
        }
        summary = summaries.get(name, "")
        if not supports_reasoning:
            summary += " Reasoning effort is unavailable for this local integration."
        self.preset_description.setText(summary.strip())

    def _preset_changed(self, label):
        name = label.lower()
        if name in OPTIMIZATION_PRESETS:
            values = OPTIMIZATION_PRESETS[name]
            self.front.setValue(values["front_matter_chars"])
            self.search.setCurrentText(values["search_context_size"])
            self.reasoning.setCurrentText(values["reasoning_effort"])
            self.output_cap.setValue(values["max_output_tokens"])
            self.evidence_urls.setValue(values["evidence_url_limit"])
        self._update_optimization_controls()

    def _status_text(self):
        data = prefs["prompt_validation"] or {}
        if not prefs["system_prompt_override"]:
            return "Using bundled prompt v%s (schema v%s)." % (PROMPT_VERSION, SCHEMA_VERSION)
        status = "validated at " + data.get("validation_timestamp", "unknown") if data else "validation required"
        if data and (
            data.get("validated_provider") != self._provider_id()
            or data.get("validated_model") != self.model.currentText().strip()
        ):
            status += "; provider or model changed since validation—revalidation is required"
        return "Custom prompt: %s" % status

    def _prompt_changed(self):
        self._validated = None
        self.status.setText("Edited custom prompt has not been validated or saved.")

    def _provider(self, model_override=None):
        provider = self._provider_id()
        key = self.api_key.text().strip() or self._provider_keys.get(provider, "") or api_key(provider)
        return create_provider({
            "provider": provider, "api_key": key,
            "model": self.model.currentText().strip() if model_override is None else model_override,
            "endpoint": self.endpoint.text().strip(), "search_mode": self.search_mode.currentData(),
            "workspace_id": self.workspace_id.text().strip(),
            "searxng_url": self.searxng_url.text().strip(), "searxng_results": self.searxng_results.value(),
            "max_searches": self.max_searches.value(), "timeout": self.timeout.value(), "search": self.search.currentText(),
            "reasoning": effective_reasoning(provider, self.reasoning.currentText()), "output_cap": self.output_cap.value(),
            "evidence_urls": self.evidence_urls.value(), "allow_remote_endpoints": prefs["allow_remote_endpoints"],
        })

    def validate_prompt(self):
        proposed = self.prompt.toPlainText().strip()
        if not proposed:
            self._validated = "default"
            self.status.setText("Empty override is valid and will use the bundled default.")
            return True
        QApplication.setOverrideCursor(__import__("qt.core", fromlist=["Qt"]).Qt.CursorShape.WaitCursor)
        try:
            result = validate_and_repair_prompt(self._provider(), proposed)
        except (PromptValidationError, ProviderError, Exception) as exc:
            QMessageBox.critical(self, "Prompt validation failed", str(exc))
            return False
        finally:
            QApplication.restoreOverrideCursor()
        if result.repaired:
            message = "The prompt needed repair.\n\n%s\n\nReplace your edit with the repaired prompt?" % (result.change_summary or "Required response-contract instructions were added.")
            if QMessageBox.question(self, "Accept repaired prompt", message) != QMessageBox.StandardButton.Yes:
                self.status.setText("Repair rejected; the previous accepted prompt remains active.")
                return False
            self.prompt.blockSignals(True); self.prompt.setPlainText(result.accepted_prompt); self.prompt.blockSignals(False)
        self._validated = result
        self.status.setText("Prompt passed review and a synthetic schema test.")
        return True

    def restore_default(self):
        self.prompt.clear(); self._validated = "default"; self.status.setText("Bundled default will be used after saving.")

    def preview(self):
        value = self.prompt.toPlainText().strip() or DEFAULT_SYSTEM_PROMPT
        QMessageBox.information(self, "Effective system prompt", value)

    def view_default(self):
        dialog = QDialog(self); dialog.setWindowTitle("Bundled default system prompt"); dialog.resize(760, 620)
        layout = QVBoxLayout(dialog); label = QLabel("This is the bundled prompt used when the override is empty.")
        label.setWordWrap(True); layout.addWidget(label)
        viewer = QPlainTextEdit(); viewer.setReadOnly(True); viewer.setPlainText(DEFAULT_SYSTEM_PROMPT); layout.addWidget(viewer)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
        dialog.exec()

    def copy_default(self):
        QApplication.clipboard().setText(DEFAULT_SYSTEM_PROMPT)

    def test_connection(self):
        try:
            ok = self._provider().test_connection()
            QMessageBox.information(self, "Connection test", "Connection succeeded." if ok else "The API returned an unexpected result.")
        except Exception as exc:
            QMessageBox.critical(self, "Connection test failed", str(exc))

    def _refresh_models_if_stale(self):
        if not cache_is_fresh(prefs, provider=self._provider_id()):
            self.refresh_model_choices(automatic=True)

    def refresh_model_choices(self, checked=False, automatic=False):
        provider_id = self._provider_id()
        key = self.api_key.text().strip() or self._provider_keys.get(provider_id, "") or api_key(provider_id)
        if provider_requires_key(provider_id) and not key:
            if not automatic:
                QMessageBox.warning(self, "API key required", "Enter or configure an API key before refreshing model choices.")
            return
        current = self.model.currentText()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        provider = None
        try:
            provider = self._provider(model_id_for_discovery(current))
            models = provider.list_models()
            if provider_id == "openai":
                choices = normalize_models(models, current)
            elif provider_id == "anthropic":
                choices = sanitize_anthropic_models(models + ([current] if current else []))
            else:
                choices = sanitize_model_list(models + ([current] if current else []))
            store_models(prefs, models, provider=provider_id)
            if not choices:
                guidance = (
                    "No compatible Claude model was returned for this account."
                    if provider_id == "anthropic" else
                    "No Ollama models are installed. Pull a schema-capable instruct model with 'ollama pull <model>', then refresh again."
                    if provider_id == "ollama" else
                    "No LM Studio model is loaded. Load a schema-capable instruct model, start the local server, then refresh again."
                )
                self.model_status.setText(guidance)
                if not automatic:
                    QMessageBox.warning(self, "No compatible models found", guidance)
                return
            self.model.blockSignals(True); self.model.clear(); self.model.addItems(choices)
            self.model.setCurrentText(current if current in choices else choices[0]); self.model.blockSignals(False)
            self.model_status.setText("Model choices refreshed and cached for seven days. Capability support is verified separately.")
            if not automatic:
                QMessageBox.information(self, "Model choices refreshed", "Found %d relevant account-visible model choice(s)." % len(choices))
        except Exception as exc:
            self.model_status.setText("Could not refresh model choices; cached choices remain available.")
            if not automatic:
                QMessageBox.critical(self, "Model refresh failed", str(exc))
        finally:
            if provider is not None:
                provider.clear_api_key()
            QApplication.restoreOverrideCursor()

    def test_capabilities(self):
        warning = "This live capability test contacts the selected model and search provider. Hosted services may charge for it. Continue?"
        if QMessageBox.question(self, "Test model capabilities?", warning) != QMessageBox.StandardButton.Yes:
            return
        try:
            result = self._provider().test_capabilities()
            capability_usage = dict(result["usage"])
            capability_usage["estimated_cost_usd"] = estimate_cost_usd(
                self.model.currentText().strip(), capability_usage,
                provider=self._provider_id(),
            )
            lines = [
                "Model API: %s" % ("supported" if result["responses_api"] else "failed"),
                "Strict structured output: %s" % ("supported" if result["structured_output"] else "failed"),
                "%s search: %s" % ("SearXNG" if self.search_mode.currentData() == "searxng" else "Hosted web", "supported" if result["web_search"] else "failed"),
                "Configured reasoning: %s" % (
                    "accepted" if result["reasoning"] else "not provided by this integration"
                ),
                "Usage: %s" % format_usage(
                    self.model.currentText().strip(), capability_usage,
                    self._provider_id(),
                ),
            ]
            QMessageBox.information(self, "Model capability result", "\n".join(lines))
        except Exception as exc:
            QMessageBox.critical(self, "Model capability test failed", str(exc))

    def copy_diagnostics(self):
        version = ".".join(map(str, PLUGIN_VERSION))
        QApplication.clipboard().setText(diagnostic_report(prefs, version, len(SESSION_LOOKUP_CACHE), len(metrics_store.records())))
        QMessageBox.information(self, "Diagnostics copied", "A redacted diagnostic report was copied to the clipboard.")

    def forget_api_key(self):
        provider = self._provider_id()
        message = "Delete the stored BiblioSleuth AI API key from the credential vault and this Calibre session?"
        if self._environment_key:
            message += "\n\nThe provider environment variable will remain active because it cannot be removed by the plugin."
        if QMessageBox.question(self, "Delete stored API key?", message) != QMessageBox.StandardButton.Yes:
            return
        self.api_key.clear()
        forget_session_api_key(provider)
        try:
            credentials.delete(provider)
        except credentials.CredentialStoreError as exc:
            QMessageBox.warning(self, "Credential vault", str(exc))
        self._has_existing_key = bool(self._environment_key)
        self.api_key.setPlaceholderText(
            "Using environment variable" if self._environment_key else "API key"
        )
        self.api_key_label.setText(self._api_key_field_label())
        self.delete_key_button.setEnabled(self._has_existing_key)
        self.key_status.setText(self._key_status_text(deleted=True))

    def _api_key_field_label(self):
        if self._environment_key:
            return "API key (environment)"
        if not provider_requires_key(self._provider_id()): return "Local server token (optional)"
        return "Replace API key" if self._has_existing_key else "API key"

    def _key_status_text(self, deleted=False):
        if self._environment_key:
            suffix = " The environment key remains active." if deleted else ""
            return "✓ API key configured by the provider environment variable. The stored value is intentionally not displayed.%s" % suffix
        if self._has_existing_key:
            return "✓ API key is stored securely and active. It is intentionally not displayed. Type a new key above to replace it; leaving the field blank keeps the stored key."
        if not provider_requires_key(self._provider_id()):
            return "No local-server token is configured. This is normal unless authentication was enabled in the server."
        return "No API key is configured. Enter one above; secure storage is used when enabled and available."

    def test_searxng(self):
        try:
            client = SearXNGClient(
                self.searxng_url.text().strip(), timeout=self.timeout.value(),
                result_limit=self.searxng_results.value(),
                allow_remote=prefs["allow_remote_endpoints"],
            )
            results = client.search("BiblioSleuth AI book metadata")
            QMessageBox.information(self, "SearXNG test", "Connection succeeded and returned %d safe web result(s)." % len(results))
        except Exception as exc:
            QMessageBox.critical(self, "SearXNG test failed", str(exc))

    def show_documentation(self):
        DocumentationDialog(self).exec()

    def show_statistics(self):
        StatisticsDialog(metrics_store, self).exec()

    def clear_statistics(self):
        if QMessageBox.question(self, "Clear all statistics?", "Permanently delete all locally stored BiblioSleuth AI statistics?") != QMessageBox.StandardButton.Yes: return
        count = metrics_store.clear(); QMessageBox.information(self, "Statistics cleared", "Deleted %d record(s)." % count)

    def save_settings(self):
        proposed = self.prompt.toPlainText().strip()
        current = prefs["system_prompt_override"].strip()
        if proposed != current and self._validated is None and not self.validate_prompt():
            raise ValueError("The custom system prompt was not accepted")
        # Validation may have replaced the editor contents with a repaired prompt.
        proposed = self.prompt.toPlainText().strip()
        if proposed and self._validated not in (None, "default"):
            if not validation_matches_prompt(proposed, {"prompt_hash": self._validated.prompt_hash}):
                raise ValueError("The custom system prompt changed after validation")
        provider = self._provider_id()
        replacement_key = self.api_key.text().strip() or self._provider_keys.get(provider, "")
        if replacement_key: self._provider_keys[provider] = replacement_key
        if not self._environment_key:
            if replacement_key:
                set_session_api_key(replacement_key, provider)
                self._has_existing_key = True
        if self.remember_key.isChecked():
            for key_provider, key_value in self._provider_keys.items():
                if key_value and not self._environment_key_for(key_provider): credentials.save(key_value, key_provider)
        else:
            for key_provider in ("openai", "anthropic", "ollama", "lmstudio"):
                credentials.delete(key_provider)
        prefs["remember_api_key"] = self.remember_key.isChecked()
        self._provider_models[provider] = self.model.currentText().strip()
        if provider in ("ollama", "lmstudio"): self._provider_endpoints[provider] = self.endpoint.text().strip()
        prefs["provider"] = provider; prefs["provider_models"] = self._provider_models; prefs["provider_endpoints"] = self._provider_endpoints
        if not resolve_anthropic_workspace_id():
            prefs["anthropic_workspace_id"] = self.workspace_id.text().strip()
        prefs["model"] = self.model.currentText().strip(); prefs["timeout"] = self.timeout.value()
        prefs["search_mode"] = self.search_mode.currentData(); prefs["searxng_url"] = self.searxng_url.text().strip()
        prefs["max_searches"] = self.max_searches.value(); prefs["searxng_results"] = self.searxng_results.value()
        prefs["optimization_preset"] = self.preset.currentText().lower()
        prefs["search_context_size"] = self.search.currentText(); prefs["front_matter_chars"] = self.front.value()
        prefs["reasoning_effort"] = self.reasoning.currentText(); prefs["max_output_tokens"] = self.output_cap.value()
        prefs["evidence_url_limit"] = self.evidence_urls.value()
        prefs["tag_limit"] = self.tags.value(); prefs["description_limit"] = self.description.value()
        prefs["statistics_enabled"] = self.statistics_enabled.isChecked()
        prefs["statistics_retention_days"] = self.statistics_days.value()
        prefs["statistics_max_records"] = self.statistics_records.value()
        metrics_store.configure(prefs["statistics_enabled"], prefs["statistics_max_records"], prefs["statistics_retention_days"])
        prefs["system_prompt_override"] = proposed
        if not proposed:
            prefs["prompt_validation"] = {}
        elif self._validated and self._validated != "default":
            prefs["prompt_validation"] = {
                key: getattr(self._validated, key) for key in (
                    "validation_timestamp", "prompt_hash", "prompt_version", "schema_version",
                    "validated_model", "validated_provider",
                )
            }
