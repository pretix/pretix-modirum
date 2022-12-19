from django.utils.translation import gettext_lazy
from . import __version__

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")


class PluginApp(PluginConfig):
    default = True
    name = 'pretix_modirum'
    verbose_name = 'Modirum payments for pretix'

    class PretixPluginMeta:
        name = gettext_lazy('Modirum payments for pretix')
        author = 'Martin Gross'
        description = gettext_lazy('Integration for payment providers based on the Modirum platform')
        visible = True
        version = __version__
        compatibility = "pretix>=2.7.0"

    def ready(self):
        from . import signals  # NOQA


