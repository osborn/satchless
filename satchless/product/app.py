from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.shortcuts import redirect

from ..core.app import SatchlessApp, view
from ..util import JSONResponse

from . import models
from ..cart import forms, signals, app

class ProductApp(SatchlessApp):

    app_name = 'product'
    namespace = 'product'
    Product = None
    Variant = None
    product_view_handlers_queue = None

    def __init__(self, *args, **kwargs):
        super(ProductApp, self).__init__(*args, **kwargs)
        self.product_view_handlers_queue = set()
        assert self.Product, ('You need to subclass ProductApp and provide'
                              ' Product')
        assert self.Variant, ('You need to subclass ProductApp and provide'
                              ' Variant')

    def get_product(self, request, product_pk, product_slug):
        product = get_object_or_404(self.Product, pk=product_pk,
                                    slug=product_slug)
        return product.get_subtype_instance()

    def get_product_details_templates(self, product):
        return ['satchless/product/view.html']

    @view(r'^\+(?P<product_pk>[0-9]+)-(?P<product_slug>[a-z0-9_-]+)/$',
          name='details')
    def product_details(self, request, extra_context={}, product=None, **kwargs):
        if not product:
            try:
                product = self.get_product(request, **kwargs)
            except ObjectDoesNotExist:
                return HttpResponseNotFound()
            
        context = dict(extra_context)
        context['variants'] = [variant.get_subtype_instance() for variant in
                self.Variant.objects.filter(product = product)]
        context['product'] = product
        context = self.get_context_data(request, **context)
        templates = self.get_product_details_templates(product)
        return TemplateResponse(request, templates, context)

    def register_product_view_handler(self, handler):
        self.product_view_handlers_queue.add(handler)


class ProductWithAddToCartFormApp(ProductApp, app.BasicMagicCartApp):
    def __init__(self, cart_class, addtocart_formclass=forms.AddToCartForm,
                 *args, **kwargs):
        super(ProductWithAddToCartFormApp, self).__init__(*args, **kwargs)
        self.addtocart_formclass = addtocart_formclass
        self.Cart = cart_class
        
    @view(r'^\+(?P<product_pk>[0-9]+)-(?P<product_slug>[a-z0-9_-]+)/$',
          name='details')
    def product_details(self, request, **kwargs):
        try:
            product = self.get_product(request, **kwargs)
        except ObjectDoesNotExist:
            return HttpResponseNotFound()
        cart = self.get_cart_for_request(request)
        Form = forms.add_to_cart_variant_form_for_product(product,
                    addtocart_formclass=self.addtocart_formclass)
        # TODO: remove hardcoded type
        if request.method == 'POST':
            form = Form(request.POST, product=product, cart=cart, typ='cart')
        else:
            form = Form(product=product, cart=cart, typ='cart')
        
        response = super(ProductWithAddToCartFormApp, self).product_details(
        request, extra_context={'cart_form':form}, product=product, **kwargs)

        if form.is_valid():
            form_result = form.save()
            #self.cart_item_added(request, form_result)
            if request.is_ajax():
                # FIXME: add cart details like number of items and new total
                response = JSONResponse({})
            else:
                response = redirect(self.reverse('details',
                                             kwargs = {'product_pk':product.id,
                                            'product_slug':product.slug}))
        elif request.is_ajax() and form.errors:
            data = dict(form.errors)
            response = JSONResponse(data, status=400)

        print form.errors
        return response

    def cart_item_added(self, request, form_result):
        signals.cart_item_added.send(sender=type(form_result.cart_item),
                                                 instance=form_result.cart_item,
                                                 result=form_result,
                                                 request=request)


class MagicProductApp(ProductWithAddToCartFormApp):

    def __init__(self, **kwargs):
        self.Product = (self.Product or
                        self.construct_product_class())
        self.Variant = (self.Variant or
                        self.construct_variant_class(self.Product))
        super(MagicProductApp, self).__init__(**kwargs)

    def construct_product_class(self):
        class Product(models.Product):
            pass
        return Product

    def construct_variant_class(self, product_class):
        class Variant(models.Variant):
            pass
        return Variant