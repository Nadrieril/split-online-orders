#!/usr/bin/env python3
"""
Usage: ./process_sainsburys_pdf.py <pdf file>
Pass it the pdf you got from sainsbury's. Let's hope they don't change the format too often.
It will output a csv that can be pasted where relevant.
"""
import os, sys, re, json, csv

import pdftotext

from utils import JSON_ARGS
from lib import Amount, Item, Report, amount_parser

EMPTY_RE = re.compile("^\s*$")
ITEM_LIST_RE = re.compile("^Delivery summary \((\d+) items\)$")
PRICE_RE = re.compile("^(-?£\d+\.\d\d)$")
QTY_RE = re.compile("^(\d+) (.*)$")
SUMMARY_RE = re.compile("^Order summary$")
SUBTOTAL_RE = re.compile("^Subtotal \((\d+) items\)$")

def parse_sainsburys_text(text: str) -> Report:
    lines = (line for line in text.split("\n") if EMPTY_RE.match(line) is None)

    # Skip until the start of item list
    for line in lines:
        if m := ITEM_LIST_RE.match(line):
            total_qty = int(m.group(1))
            break
    assert(total_qty is not None)

    # Gather items until "Order summary". Each line is either part of a name or is a price for the
    # previous item.
    current_name = []
    items = []
    for line in lines:
        if SUMMARY_RE.match(line) is not None:
            break
        elif m := PRICE_RE.match(line):
            name = " ".join(current_name)
            price = Amount(m.group(1))
            current_name = []

            qty = 1
            if m := QTY_RE.match(name):
                qty = int(m.group(1))
                name = m.group(2)
            item = Item(name=name, qty=qty, price=price)
            items.append(item)
        else:
            current_name.append(line)

    # Here we have a broken table: the columns are not interleaved but concatenated.
    first_col = []
    coupons = 0
    for line in lines:
        if line == "Total paid":
            break
        if m := PRICE_RE.match(line):
            price = Amount(m.group(1))
            name = first_col.pop(0)
            if name == "Delivery cost":
                delivery = price
            elif SUBTOTAL_RE.match(name):
                subtotal = price
            elif name == "Coupons":
                coupons = price
            else:
                raise Exception(f"Don't know how to handle column {name}")
        else:
            first_col.append(line)
    assert(len(first_col) == 0)

    # Finally remains the total price
    m = PRICE_RE.match(next(lines))
    total = Amount(m.group(1))

    report = Report(items=items, shared_cost=coupons + delivery)
    assert(report.total_item_price + delivery == subtotal)
    assert(subtotal + coupons == total)
    assert(report.total_item_qty == total_qty)
    assert(report.total_price == total)

    return report

def parse_sainsburys_pdf_file(path):
    with open(path, "rb") as f:
        pdf = pdftotext.PDF(f)
    text = "\n".join(pdf)
    return parse_sainsburys_text(text)

if __name__ == "__main__":
    report = parse_sainsburys_pdf_file(sys.argv[1])
    report.to_csv(sys.stdout)
