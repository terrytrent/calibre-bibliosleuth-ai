import os

from qt.core import QLabel, QComboBox, QFormLayout, QLineEdit, QMessageBox, QWizard, QWizardPage

from . import credentials
from .prefs import prefs, set_session_api_key
from .providers import PROVIDER_LABELS


class SetupWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to BiblioSleuth AI")
        self.resize(680, 460)

        welcome = QWizardPage(); welcome.setTitle("Welcome to BiblioSleuth AI")
        welcome_layout = QFormLayout(welcome)
        intro = QLabel(
            "BiblioSleuth AI researches exact-edition EPUB metadata with your chosen AI and web-search provider, then lets you review every field before applying it. "
            "It never rewrites the EPUB."
        )
        intro.setWordWrap(True); welcome_layout.addRow(intro)
        self.addPage(welcome)

        access = QWizardPage(); access.setTitle("Choose an AI provider")
        access_layout = QFormLayout(access)
        self.provider = QComboBox()
        for provider_id, label in PROVIDER_LABELS.items(): self.provider.addItem(label, provider_id)
        self.provider.setCurrentIndex(max(0, self.provider.findData(prefs["provider"])))
        access_layout.addRow("AI provider", self.provider)
        self.api_key = QLineEdit(); self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("Paste a provider key/token, or leave blank to configure later")
        access_layout.addRow("API key or local token", self.api_key)
        key_note = QLabel("The key is saved in the operating-system credential vault when available, never in Calibre JSON preferences.")
        key_note.setWordWrap(True); access_layout.addRow(key_note)
        self.addPage(access)

        choices = QWizardPage(); choices.setTitle("Choose a starting preset")
        choices_layout = QFormLayout(choices)
        self.preset = QComboBox(); self.preset.addItems(["Balanced", "Economy", "Thorough"])
        choices_layout.addRow("Optimization preset", self.preset)
        preset_note = QLabel("Balanced is recommended. Economy minimizes cost; Thorough spends more context and reasoning on difficult editions.")
        preset_note.setWordWrap(True); choices_layout.addRow(preset_note)
        self.addPage(choices)

        finish = QWizardPage(); finish.setTitle("Add BiblioSleuth AI to the toolbar")
        finish_layout = QFormLayout(finish)
        toolbar = QLabel(
            "If the icon is not visible, open Preferences → Toolbars & menus and add BiblioSleuth AI. "
            "Click the main icon to research; use its arrow for settings, documentation, fresh research, cache, diagnostics, and undo."
        )
        toolbar.setWordWrap(True); finish_layout.addRow(toolbar)
        privacy = QLabel(
            "Only selected OPF fields and confidently identified title/copyright-page text are sent; unidentified pages and chapters are excluded. API calls and web search may incur charges. "
            "Anonymized local performance statistics are enabled by default and can be disabled or cleared in the Statistics settings tab."
        )
        privacy.setWordWrap(True); finish_layout.addRow(privacy)
        local_note = QLabel(
            "Ollama and LM Studio setup continues in the full configuration screen, "
            "where you select a loaded model, confirm the endpoint, configure SearXNG, "
            "and run both readiness tests."
        )
        local_note.setWordWrap(True); finish_layout.addRow(local_note)
        self.addPage(finish)

    def accept(self):
        provider = self.provider.currentData() or "openai"
        key = self.api_key.text().strip()
        if key:
            set_session_api_key(key, provider)
            if credentials.available():
                try:
                    credentials.save(key, provider); prefs["remember_api_key"] = True
                except Exception as exc:
                    QMessageBox.warning(self, "Credential vault", "The key is active for this session but could not be saved securely: %s" % exc)
        prefs["provider"] = provider
        if provider in ("ollama", "lmstudio"): prefs["search_mode"] = "searxng"
        prefs["optimization_preset"] = self.preset.currentText().lower()
        prefs["onboarding_complete"] = True
        super().accept()
