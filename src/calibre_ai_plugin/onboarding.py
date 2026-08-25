import os

from qt.core import QLabel, QComboBox, QFormLayout, QLineEdit, QMessageBox, QWizard, QWizardPage

from . import credentials
from .prefs import prefs, set_session_api_key


class SetupWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to BiblioSleuth AI")
        self.resize(680, 460)

        welcome = QWizardPage(); welcome.setTitle("Welcome to BiblioSleuth AI")
        welcome_layout = QFormLayout(welcome)
        intro = QLabel(
            "BiblioSleuth AI researches exact-edition EPUB metadata with OpenAI web search, then lets you review every field before applying it. "
            "It never rewrites the EPUB."
        )
        intro.setWordWrap(True); welcome_layout.addRow(intro)
        self.addPage(welcome)

        access = QWizardPage(); access.setTitle("OpenAI access")
        access_layout = QFormLayout(access)
        self.api_key = QLineEdit(); self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        if os.environ.get("OPENAI_API_KEY"):
            self.api_key.setPlaceholderText("Using OPENAI_API_KEY"); self.api_key.setEnabled(False)
        else:
            self.api_key.setPlaceholderText("Paste an API key, or leave blank to configure later")
        access_layout.addRow("API key", self.api_key)
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
        self.addPage(finish)

    def accept(self):
        key = self.api_key.text().strip()
        if key:
            set_session_api_key(key)
            if credentials.available():
                try:
                    credentials.save(key); prefs["remember_api_key"] = True
                except Exception as exc:
                    QMessageBox.warning(self, "Credential vault", "The key is active for this session but could not be saved securely: %s" % exc)
        prefs["optimization_preset"] = self.preset.currentText().lower()
        prefs["onboarding_complete"] = True
        super().accept()
