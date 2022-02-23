#!/usr/bin/env python3
"""
Usage: ./process_waitrose_email.py <eml file>
Pass it the email you got from waitrose. Let's hope they don't change the format too often.
It will output a csv that can be pasted where relevant.
"""
import os, sys, re, json, csv

from bs4 import BeautifulSoup
from email import policy, message_from_binary_file

from utils import JSON_ARGS
from lib import Amount, Item, Report, amount_parser

def parse_waitrose_html(html: str) -> Report:
    # Parse html message
    document = BeautifulSoup(html, 'html.parser')

    # Find the order details
    order_headers = document.find_all(text=re.compile('Your Order'))
    assert(len(order_headers) == 1)
    order_div = order_headers[0].parent
    order_table = order_div.find_next_sibling('table')
    assert(order_table is not None)
    subtables = order_table.find_all('table')

    # Remove headers
    while list(subtables[0].stripped_strings) == ['Qty', 'Price']:
        subtables.pop(0)

    # There's one table per item
    items = []
    for st in subtables:
        rows = st.find_all('tr')
        # The table has 1 row if just an item and 2 rows if the item had a sale
        assert(1 <= len(rows) <= 2)

        item_cols = rows[0].find_all('td')
        assert(len(item_cols) == 4)
        name = item_cols[1].string.strip().replace(' ‡', '')
        qty = item_cols[2].get_text().strip()
        qty = re.sub(r" *x.*", "", qty)
        price = Amount(item_cols[3].string)
        item = Item(name, qty, price)

        if len(rows) == 2:
            sale_cols = rows[1].find_all('td')
            assert(len(sale_cols) == 3)
            discount = Amount(sale_cols[2].string)
            item.add_discount(discount)

        items.append(item)

    # Find the order summary
    order_summary_headers = document.find_all(text=re.compile('Order Summary'))
    assert(len(order_summary_headers) == 1)
    summary_table = order_summary_headers[0].find_parent('table')
    def table_entry(name):
        return summary_table.find(text=re.compile(name)).parent.find_next_sibling('td').string

    vouchers = summary_table.find(text=re.compile('Promotion Discount:')).find_parent('tr')
    vouchers = vouchers.find_next_sibling('tr').find_next_sibling('tr')
    vouchers = vouchers.find(text=amount_parser.regex)
    vouchers = Amount(vouchers)

    delivery = table_entry('Delivery:')
    delivery = Amount(delivery)

    report = Report(items=items, shared_cost=vouchers+delivery)

    # Check totals to be sure we didn't fail to parse anything.
    total_qty = table_entry('Number of Items:')
    total_qty = int(total_qty.strip())
    assert(total_qty == report.total_item_qty)

    subtotal = table_entry('Subtotal:')
    subtotal = Amount(subtotal)
    assert(subtotal == report.total_item_price_without_discounts)

    offers = table_entry('Offers:')
    offers = Amount(offers)
    assert(offers == report.total_item_discounts)
    assert(subtotal + offers == report.total_item_price)

    total = table_entry('Total:')
    total = Amount(total)
    assert(total == report.total_price)

    return report

def parse_waitrose_eml_file(path):
    with open(path, 'rb') as f:
        msg = message_from_binary_file(f, policy=policy.default)
    html = msg.get_body(preferencelist=['html']).get_content()
    return parse_waitrose_html(html)

if __name__ == "__main__":
    report = parse_waitrose_eml_file(sys.argv[1])
    # print(json.dumps(report, **JSON_ARGS))
    writer = csv.writer(sys.stdout, delimiter=',')
    writer.writerow(["Shared cost", report.shared_cost])
    writer.writerow(["Name", "Qty", "Price"])
    for item in report.items_split_qty:
        writer.writerow([item.name, item.qty, item.price])

