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

    # It's not semantically formatted. We have to iterate through in order to get the info.
    discounts = 0
    currently_listing_savings = False
    currently_listing_discounts = False
    for entry in summary_table.find_all('tr'):
        entry_name = entry.find('td').string.strip()
        get_contents = lambda: entry.find('td').find_next_sibling('td').string.strip()
        match entry_name:
            case "Order Summary":
                pass
            case "Number of Items:":
                total_qty = int(get_contents())
            case "Subtotal:":
                subtotal = Amount(get_contents())
            case "Your savings":
                currently_listing_savings = True
            case "Promotion Discount:":
                currently_listing_discounts = True
            case "":
                amt = Amount(get_contents())
                if currently_listing_savings or currently_listing_discounts:
                    discounts += amt
                    currently_listing_savings = False
                    currently_listing_discounts = False
                else:
                    raise Exception(f"Dunno what this amount corresponds to: {amt}")
            case "Offers:":
                offers = Amount(get_contents())
                # Offers are already counted in the item prices but are counted in savings, so we
                # avoid double-counting here.
                discounts -= offers
            case "Delivery:":
                delivery = Amount(get_contents())
            case "Total:":
                total = Amount(get_contents())
            case _:
                if not (currently_listing_discounts or currently_listing_savings):
                    raise Exception(f"Dunno what this corresponds to: {entry_name}")

    report = Report(items=items, shared_cost=discounts+delivery)

    # Check totals to be sure we didn't fail to parse anything.
    assert(total_qty == report.total_item_qty)

    assert(subtotal == report.total_item_price_without_discounts)

    assert(offers == report.total_item_discounts)
    assert(subtotal + offers == report.total_item_price)

    assert(total == report.total_price)

    return report

def parse_waitrose_eml_file(path):
    with open(path, 'rb') as f:
        msg = message_from_binary_file(f, policy=policy.default)
    html = msg.get_body(preferencelist=['html']).get_content()
    return parse_waitrose_html(html)

if __name__ == "__main__":
    report = parse_waitrose_eml_file(sys.argv[1])
    report.upload_to_google_sheets()
