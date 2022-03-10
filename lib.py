import io, math, re, json, csv
from numbers import Number
from dataclasses import dataclass
from functools import total_ordering
from typing import List, Optional

class AmountParser:
    def __init__(self):
        noncap = lambda x: "(?:" + x + ")"
        opt = lambda x: noncap(x) + "?"
        cap = lambda x: "(" + x + ")"
        compile = lambda x: re.compile("^" + x + "$")

        sp = "\s*"
        currency = "[€$£]|[a-zA-Z]+"
        float = opt("-\s?") + "[0-9.,]+"
        sign = "-"
        amount = sp + opt(cap(sign)) + opt(cap(currency)) + sp + cap(float) + sp + opt(cap(currency)) + sp
        self.regex = compile(amount)

    def parse_amount(self, s: str) -> Optional['Amount']:
        m = self.regex.match(s)
        if m is None:
            return None
        (sign, cur1, amt, cur2) = m.groups()
        cur = cur1 or cur2
        amt = Amount(float(amt.replace(',', '')), cur1 or cur2)
        if sign is not None:
            amt = -amt
        return amt
amount_parser = AmountParser()

class DifferentCurrency(Exception): pass

@total_ordering
class Amount:
    quantity: float
    currency: Optional[str]

    def __init__(self, quantity, currency=None):
        if isinstance(quantity, Number):
            self.quantity = quantity
            self.currency = None
        elif isinstance(quantity, str):
            amt = amount_parser.parse_amount(quantity)
            assert(amt is not None)
            self.quantity = amt.quantity
            self.currency = amt.currency
        elif isinstance(quantity, Amount):
            self.quantity = quantity.quantity
            self.currency = quantity.currency
        else:
            raise Exception(f"Unknown type: {type(quantity)}")

        if currency is not None:
            self.currency = currency.strip()

    def __add__(self, other):
        if isinstance(other, Number):
            return Amount(self.quantity + other, self.currency)
        elif self.quantity == 0:
            return other
        elif other.quantity == 0:
            return self
        elif self.currency != other.currency:
            raise DifferentCurrency
        else:
            return Amount(self.quantity + other.quantity, self.currency)
    def __radd__(self, other):
        return self + other
    def __sub__(self, other):
        return self + (-other)
    def __rsub__(self, other):
        return (-self) + other
    def __neg__(self):
        return Amount(-self.quantity, self.currency)
    def __truediv__(self, other):
        assert(isinstance(other, Number))
        return Amount(self.quantity / other, self.currency)

    def abs(self) -> 'Amount':
        if self >= 0:
            return self
        else:
            return -self

    def __str__(self):
        return f"{self.currency}{self.quantity:.2f}"
    def __repr__(self):
        return str(self)
    def __json__(self):
        return str(self)

    def compare(self, other, fn):
        if isinstance(other, Amount):
            if self.currency != other.currency:
                raise DifferentCurrency
            return fn(self.quantity, other.quantity)
        if isinstance(other, Number):
            return fn(self.quantity, other)
        return NotImplemented
    def __eq__(self, other):
        return self.compare(other, lambda x,y: math.isclose(x, y))
    def __lt__(self, other):
        return self.compare(other, lambda x,y: x.__lt__(y))

@total_ordering
@dataclass
class Item:
    name: str
    qty: int | str
    price_without_discount: Amount
    discount: Amount

    def __init__(self, name, qty, price):
        self.name = name
        if isinstance(qty, int):
            self.qty = qty
        elif isinstance(qty, str):
            if qty.isnumeric():
                self.qty = int(qty)
            else:
                self.qty = 1
        else:
            raise Exception(f"Unknown type: {type(qty)}")
        self.price_without_discount = Amount(price)
        self.discount = Amount(0, self.price_without_discount.currency)

    def add_discount(self, d: Amount):
        self.discount += d

    def with_qty_1(self) -> 'Item':
        if self.qty == 1:
            return self
        item = Item(self.name, 1, self.price_without_discount / self.qty)
        item.add_discount(self.discount / self.qty)
        return item

    @property
    def price(self) -> Amount:
        return self.price_without_discount + self.discount

    def __json__(self):
        return {
            'name': self.name,
            'qty': self.qty,
            'price': self.price,
        }

    def _compare_key(self):
        return (self.name.lower(), self.qty)
    def __lt__(self, other):
        assert(isinstance(other, Item))
        return self._compare_key() < other._compare_key()

@dataclass
class Report:
    items: List[Item]
    # Delivery/coupons/etc
    shared_cost: Amount

    def __init__(self, items, shared_cost=0):
        self.items = list(items)
        self.items.sort()
        self.shared_cost = Amount(shared_cost)

    def __json__(self):
        return {
            'items': list(self.items_split_qty),
            'shared_cost': self.shared_cost,
        }

    def to_csv(self, output=None):
        write_to_str = output is None
        if write_to_str:
            output = io.StringIO()

        writer = csv.writer(output, delimiter=',')
        writer.writerow(["Shared cost", self.shared_cost.quantity])
        writer.writerow(["Name", "Qty", "Price"])
        for item in self.items_split_qty:
            writer.writerow([item.name.replace(",",""), item.qty, item.price.quantity])

        if write_to_str:
            return output.getvalue()

    # List each item i.qty times
    @property
    def items_split_qty(self):
        for item in self.items:
            with_q1 = item.with_qty_1()
            for _ in range(item.qty):
                yield with_q1

    @property
    def total_item_qty(self) -> int:
        return sum(i.qty for i in self.items)
    @property
    def total_item_price(self) -> Amount:
        return sum(i.price for i in self.items)
    @property
    def total_item_price_without_discounts(self) -> Amount:
        return sum(i.price_without_discount for i in self.items)
    @property
    def total_item_discounts(self) -> Amount:
        return sum(i.discount for i in self.items)
    @property
    def total_price(self) -> Amount:
        return self.total_item_price + self.shared_cost

