from qt.core import (
    QDialog, QDialogButtonBox, QLabel, QPalette, QPushButton, QTextBrowser, QVBoxLayout,
)


class DocumentationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BiblioSleuth AI documentation")
        self.resize(920, 760)
        layout = QVBoxLayout(self)
        self.browser = QTextBrowser(); self.browser.setOpenExternalLinks(True)
        try:
            content = get_resources("docs/user-guide.html").decode("utf-8")  # noqa: F821 -- injected by Calibre
        except Exception:
            content = "<h1>BiblioSleuth AI</h1><p>The bundled documentation could not be loaded.</p>"
        palette = self.browser.palette()
        colors = {
            "{{TEXT_COLOR}}": palette.color(QPalette.ColorRole.Text).name(),
            "{{BASE_COLOR}}": palette.color(QPalette.ColorRole.Base).name(),
            "{{ALT_BASE_COLOR}}": palette.color(QPalette.ColorRole.AlternateBase).name(),
            "{{LINK_COLOR}}": palette.color(QPalette.ColorRole.Link).name(),
            "{{BORDER_COLOR}}": palette.color(QPalette.ColorRole.Mid).name(),
        }
        for token, color in colors.items():
            content = content.replace(token, color)
        self.browser.setHtml(content); layout.addWidget(self.browser)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject); layout.addWidget(buttons)


class ApiKeySetupDialog(QDialog):
    CONFIGURE = 10
    DOCUMENTATION = 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set up BiblioSleuth AI")
        self.resize(560, 230)
        layout = QVBoxLayout(self)
        title = QLabel("<h2>AI provider credentials required</h2>")
        message = QLabel(
            "BiblioSleuth AI needs credentials for the selected hosted AI provider. "
            "You can enter one in the plugin settings now. The key is masked in the interface, "
            "and the provider's environment variable takes precedence. OpenAI and Claude keys are supported; local providers normally need no token."
        )
        message.setWordWrap(True); message.setOpenExternalLinks(True)
        layout.addWidget(title); layout.addWidget(message)
        configure = QPushButton("Configure API key…"); configure.clicked.connect(lambda: self.done(self.CONFIGURE))
        docs = QPushButton("Read documentation"); docs.clicked.connect(lambda: self.done(self.DOCUMENTATION))
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        layout.addWidget(configure); layout.addWidget(docs); layout.addWidget(cancel)

    @classmethod
    def choose(cls, parent=None):
        dialog = cls(parent); return dialog.exec()
