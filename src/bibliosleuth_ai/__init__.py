try:
    from calibre.customize import InterfaceActionBase
except ImportError:  # Allow the Calibre-independent core to be tested normally.
    class InterfaceActionBase:
        pass


class BiblioSleuthAIPlugin(InterfaceActionBase):
    name = "BiblioSleuth AI"
    description = "Research and review exact-edition EPUB metadata with AI"
    supported_platforms = ["windows", "osx", "linux"]
    author = "Terry Trent"
    version = (1, 0, 0)
    minimum_calibre_version = (7, 0, 0)
    actual_plugin = "calibre_plugins.bibliosleuth_ai.action:BiblioSleuthAIAction"

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.bibliosleuth_ai.config import ConfigWidget

        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()
