import json

from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _  # NoQA
from pretix.base.signals import logentry_display, register_payment_providers

from .payment import ModirumPaymentProvider


@receiver(register_payment_providers, dispatch_uid="payment_modirum")
def register_payment_provider(sender, **kwargs):
    return ModirumPaymentProvider


@receiver(signal=logentry_display, dispatch_uid="modirum_logentry_display")
def logentry_display(sender, logentry, **kwargs):
    if logentry.action_type != 'pretix_modirum.modirum.event':
        return

    data = json.loads(logentry.data)
    plains = {
        'AUTHORIZED': _('Payment was successful.'),
        'CAPTURED': _('Payment was successful.'),
        'CANCELED': _('Payment failed, user canceled the process.'),
        'REFUSED': _('Payment failed, payment was denied by card or bank.'),
        'ERROR': _('Non recoverable system or other error occurred during payment process.'),
    }

    return _('Modirum reported an event: {}').format(plains.get(data.get('status'), ''))
