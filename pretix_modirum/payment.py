import base64
import hashlib
from collections import OrderedDict
from decimal import Decimal

from django import forms
from django.http import HttpRequest
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _  # NoQA
from pretix.base.models import Order, OrderPayment
from pretix.base.payment import BasePaymentProvider
from pretix.multidomain.urlreverse import build_absolute_uri, eventreverse


class ModirumPaymentProvider(BasePaymentProvider):
    identifier = 'modirum'
    verbose_name = _('Credit card via Modirum')
    public_name = _('Credit card')

    @property
    def settings_form_fields(self) -> dict:
        d = OrderedDict(
            [
                ('test_gateway_url', forms.CharField(
                    label='{} ({})'.format(_('Payment Gateway URL'), _('Test Environment')),
                    help_text=_('The URL should have a format of '
                                'https://acquirername.environment.modirum.com/vpos/shophandlermpi'),
                    required=False,
                )),
                ('test_gateway_mid', forms.CharField(
                    label='{} ({})'.format(_('Merchant ID'), _('Test Environment')),
                    required=False,
                )),
                ('test_gateway_secret', forms.CharField(
                    label='{} ({})'.format(_('Shared Digest Secret'), _('Test Environment')),
                    help_text=_('Digest used to de- and encrypt messages to the payment gateway.'),
                    required=False,
                )),
                ('prod_gateway_url', forms.CharField(
                    label='{} ({})'.format(_('Payment Gateway URL'), _('Production Environment')),
                    help_text=_('The URL should have a format of '
                                'https://acquirername.environment.modirum.com/vpos/shophandlermpi'),
                    required=False,
                )),
                ('prod_gateway_mid', forms.CharField(
                    label='{} ({})'.format(_('Merchant ID'), _('Production Environment')),
                    required=False,
                )),
                ('prod_gateway_secret', forms.CharField(
                    label='{} ({})'.format(_('Shared Digest Secret'), _('Production Environment')),
                    help_text=_('Digest used to de- and encrypt messages to the payment gateway.'),
                    required=False,
                ))
            ] + list(super().settings_form_fields.items())
        )

        d.move_to_end('_enabled', last=False)
        return d

    @property
    def test_mode_message(self) -> str:
        return _("In test mode, only test cards will work.")

    def settings_content_render(self, request: HttpRequest) -> str:
        if not self.event.settings.invoice_address_required:
            return '<div class="alert alert-danger">{}</div>'.format(
                _('Modirum payments only work if the customer fills in a full invoice address, so we recommend '
                  'requiring an address in your invoicing settings.')
            )

    def payment_control_render(self, request: HttpRequest, payment: OrderPayment):
        template = get_template('pretix_modirum/control.html')
        ctx = {'request': request, 'event': self.event, 'settings': self.settings,
               'payment_info': payment.info_data, 'order': payment.order, 'provname': self.verbose_name}
        return template.render(ctx)

    def payment_form_render(self, request, **kwargs) -> str:
        template = get_template('pretix_modirum/checkout_payment_form.html')
        ctx = {'request': request, 'event': self.event, 'settings': self.settings}
        return template.render(ctx)

    def checkout_confirm_render(self, request) -> str:
        template = get_template('pretix_modirum/checkout_payment_confirm.html')
        ctx = {'request': request, 'event': self.event, 'settings': self.settings}
        return template.render(ctx)

    def checkout_prepare(self, request, total):
        return True

    def payment_is_valid_session(self, request):
        return True

    def is_allowed(self, request: HttpRequest, total: Decimal = None) -> bool:
        global_allowed = super().is_allowed(request, total) and request.event.settings.invoice_address_required

        if request.event.testmode:
            local_allowed = request.event.settings.payment_modirum_test_gateway_url \
                and request.event.settings.payment_modirum_test_gateway_mid \
                and request.event.settings.payment_modirum_test_gateway_secret
        else:
            local_allowed = request.event.settings.payment_modirum_prod_gateway_url \
                and request.event.settings.payment_modirum_prod_gateway_mid \
                and request.event.settings.payment_modirum_prod_gateway_secret

        return global_allowed and local_allowed

    def execute_payment(self, request: HttpRequest, payment: OrderPayment):
        return eventreverse(self.event, 'plugins:pretix_modirum:redirect', kwargs={
            'order': payment.order.code,
            'payment': payment.pk,
            'hash': hashlib.sha1(payment.order.secret.lower().encode()).hexdigest(),
        })

    def sign_parameters(self, params: OrderedDict, order: Order) -> OrderedDict:
        digest = ''.join(params.values())
        if order.testmode:
            digest += order.event.settings.payment_modirum_test_gateway_secret
        else:
            digest += order.event.settings.payment_modirum_prod_gateway_secret

        digest = base64.b64encode(
            hashlib.sha256(digest.encode()).digest()
        ).decode()

        params['digest'] = digest

        return params

    def params_for_payment(self, payment, request):
        hash = hashlib.sha1(payment.order.secret.lower().encode()).hexdigest()
        return OrderedDict({
            'version': '2',
            'mid': self.settings.get('test_gateway_mid') if payment.order.testmode else self.settings.get('prod_gateway_mid'),
            'lang': payment.order.locale[:2],
            'orderid': '{event}{code}P{payment}'.format(event=self.event.slug.upper(), code=payment.order.code, payment=payment.local_id),
            'orderDesc': _('Order {event}-{code}').format(event=self.event.slug.upper(), code=payment.order.code),
            'orderAmount': str(payment.amount),
            'currency': self.event.currency,
            'billCountry': str(payment.order.invoice_address.country),
            'billState': payment.order.invoice_address.state,
            'billZip': payment.order.invoice_address.zipcode,
            'billCity': payment.order.invoice_address.city,
            'billAddress': payment.order.invoice_address.street,
            'confirmUrl': build_absolute_uri(self.event, 'plugins:pretix_modirum:return', kwargs={
                'order': payment.order.code,
                'payment': payment.pk,
                'hash': hash,
            }),
            'cancelUrl': build_absolute_uri(self.event, 'plugins:pretix_modirum:return', kwargs={
                'order': payment.order.code,
                'payment': payment.pk,
                'hash': hash,
            }),
            'var1': payment.order.code,
            'var2': self.event.slug,
            'var3': self.event.organizer.slug
        })
