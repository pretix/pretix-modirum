import base64
import copy
import hashlib

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _  # NoQA
from django.views import View
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from pretix.base.models import Order, OrderPayment, Quota
from pretix.multidomain.urlreverse import eventreverse


class ModirumOrderView:
    def dispatch(self, request, *args, **kwargs):
        try:
            self.order = request.event.orders.get(code=kwargs['order'])
            if hashlib.sha1(self.order.secret.lower().encode()).hexdigest() != kwargs['hash'].lower():
                raise Http404('Unknown order')
        except Order.DoesNotExist:
            # Do a hash comparison as well to harden timing attacks
            if 'abcdefghijklmnopq'.lower() == hashlib.sha1('abcdefghijklmnopq'.encode()).hexdigest():
                raise Http404('Unknown order')
            else:
                raise Http404('Unknown order')
        return super().dispatch(request, *args, **kwargs)

    @cached_property
    def pprov(self):
        return self.payment.payment_provider

    @property
    def payment(self):
        return get_object_or_404(
            self.order.payments,
            pk=self.kwargs['payment'],
            provider__istartswith='modirum',
        )


@method_decorator(xframe_options_exempt, 'dispatch')
class RedirectView(ModirumOrderView, TemplateView):
    template_name = 'pretix_modirum/redirecting.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['url'] = self.order.event.settings.get('payment_modirum_test_gateway_url') if self.order.testmode \
            else self.order.event.settings.get('payment_modirum_prod_gateway_url')
        ctx['params'] = self.pprov.sign_parameters(
            self.pprov.params_for_payment(self.payment, self.request),
            self.order
        )
        return ctx


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(xframe_options_exempt, 'dispatch')
class ReturnView(ModirumOrderView, View):
    def get(self, request, *args, **kwargs):
        messages.error(
            request, _('The payment failed without an error message. You can click below to try again.')
        )
        return self._redirect_to_order()

    def post(self, request, *args, **kwargs):
        if not self.validate_digest(request, self.pprov):
            messages.error(self.request, _('Sorry, we could not validate the payment result. Please try again or '
                                           'contact the event organizer to check if your payment was successful.'))
            return self._redirect_to_order()

        self.order.log_action('pretix_modirum.modirum.event', data=dict(request.POST.items()))
        try:
            self.process_result(request, self.payment, self.pprov)
        except Quota.QuotaExceededException as e:
            messages.error(request, str(e))

        if request.POST.get('status') == 'CANCELED':
            messages.error(self.request, _('The payment process was canceled. You can click below to try again.'))
            return self._redirect_to_order()

        if request.POST.get('status') in ['REFUSED', 'ERROR']:
            messages.error(
                self.request, _('The payment failed with the following message: {message}. '
                                'You can click below to try again.').format(message=request.POST.get('message')))
            return self._redirect_to_order()

        return self._redirect_to_order()

    def _redirect_to_order(self):
        return redirect(eventreverse(self.request.event, 'presale:event.order', kwargs={
            'order': self.order.code,
            'secret': self.order.secret
        }) + ('?paid=yes' if self.order.status == Order.STATUS_PAID else ''))

    def validate_digest(self, request, prov):
        params = copy.deepcopy(request.POST)
        if 'digest' in params:
            postdigest = params.pop('digest')[0]

            digest = ''.join(params.values())

            if self.order.testmode:
                digest += self.order.event.settings.payment_modirum_test_gateway_secret
            else:
                digest += self.order.event.settings.payment_modirum_prod_gateway_secret

            digest = base64.b64encode(
                hashlib.sha256(digest.encode()).digest()
            ).decode()

            return digest == postdigest

        return False

    def process_result(self, request, payment, prov):
        payment.info_data = dict(request.POST.items())
        payment.save()
        if payment.state in (
                OrderPayment.PAYMENT_STATE_PENDING, OrderPayment.PAYMENT_STATE_CREATED
        ):
            if request.POST.get('status') in ['AUTHORIZED', 'CAPTURED']:
                payment.confirm()
            elif request.POST.get('status') == 'CANCELED':
                payment.state = OrderPayment.PAYMENT_STATE_CANCELED
                payment.save()
            elif request.POST.get('status') in ['REFUSED', 'ERROR']:
                payment.state = OrderPayment.PAYMENT_STATE_FAILED
                payment.save()
