from satchless.item import ItemSet, ItemLine


class CartLine(ItemLine):
    """
    Represents a cart line, ie. an ItemLine suitable for Cart use
    """
    def __init__(self, product, quantity, data=None):
        self.product = product
        self.quantity = quantity
        self.data = data

    def __eq__(self, other):
        if not isinstance(other, CartLine):
            return NotImplemented

        return (self.product == other.product and
                self.quantity == other.quantity and
                self.data == other.data)

    def __ne__(self, other):
        return not self == other  # pragma: no cover

    def __repr__(self):
        return 'CartLine(product=%r, quantity=%r, data=%r)' % (
            self.product, self.quantity, self.data)

    def __getstate__(self):
        return (self.product, self.quantity, self.data)

    def __setstate__(self, data):
        self.product, self.quantity, self.data = data

    def get_quantity(self):
        return self.quantity

    def get_price_per_item(self, **kwargs):
        return self.product.get_price(**kwargs)


class Cart(ItemSet):
    """
    Represents a Cart (Shopping Cart, Basket, etc.)
    """
    modified = False
    "'Dirty' flag in case you need to sync the cart to a persistent storage"
    _state = None
    "Internal state, do not touch"

    def __init__(self, items=None):
        self._state = []
        self.modified = True
        items = items or []
        for l in items:
            self.add(l.product, l.quantity, l.data, replace=True)

    def __repr__(self):
        return 'Cart(%r)' % (list(self),)

    def __iter__(self):
        return iter(self._state)

    def __getstate__(self):
        return self._state

    def __setstate__(self, state):
        self._state = state

    def __len__(self):
        return len(self._state)

    def __nonzero__(self):
        return bool(self._state)

    def __getitem__(self, key):
        return self._state[key]

    def count(self):
        return sum([item.get_quantity() for item in self._state])

    def check_quantity(self, product, quantity, data=None):
        return True

    def create_line(self, product, quantity=0, data=None):
        return CartLine(product, quantity, data=None)

    def get_line(self, product, data=None):
        return next(
            (cart_line for cart_line in self._state
             if cart_line.product == product and cart_line.data == data),
            None)

    def _get_or_create_line(self, product, quantity, data=None):
        cart_line = self.get_line(product, data)
        if cart_line:
            return (False, cart_line)
        else:
            return (True, self.create_line(product, quantity, data))

    def add(self, product, quantity=1, data=None, replace=False):
        created, cart_line = self._get_or_create_line(product, 0, data)

        if replace:
            new_quantity = quantity
        else:
            new_quantity = cart_line.quantity + quantity

        if new_quantity < 0:
            raise ValueError('%r is not a valid quantity (results in %r)' % (
                quantity, new_quantity))

        self.check_quantity(product, new_quantity, data)

        cart_line.quantity = new_quantity

        if not cart_line.quantity and not created:
            self._state.remove(cart_line)
            self.modified = True
        elif cart_line.quantity and created:
            self._state.append(cart_line)
            self.modified = True
        elif not created:
            self.modified = True


class CartPartition(ItemSet):
    """
    Represents a single cart partition meant for delivery
    """


class CartPartitioner(ItemSet):
    """
    Represents a cart partitioned for delivery

    Override the __iter__() method to provide custom partitioning.
    """
    def __init__(self, cart):
        self.cart = cart

    def __iter__(self):
        'Override this method to provide custom partitioning'
        yield CartPartition(list(self.cart))

    def __nonzero__(self):
        return bool(self.cart)
