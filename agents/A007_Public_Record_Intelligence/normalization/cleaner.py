def parse_amount(amount_str):
    # E.g., "$1,000,001 - $5,000,000"
    if not amount_str:
        return 0, 0
    try:
        parts = amount_str.replace("$", "").replace(",", "").split("-")
        if len(parts) == 2:
            return int(parts[0].strip()), int(parts[1].strip())
        elif len(parts) == 1:
            return int(parts[0].strip()), int(parts[0].strip())
    except ValueError:
        pass
    return 0, 0

def normalize_trade(raw_trade):
    amount_min, amount_max = parse_amount(raw_trade.get("amount", ""))

    return {
        "id": raw_trade.get("id"),
        "politician": raw_trade.get("politician"),
        "ticker": raw_trade.get("ticker", "").upper(),
        "transaction_date": raw_trade.get("transaction_date"),
        "filing_date": raw_trade.get("filing_date"),
        "transaction_type": raw_trade.get("transaction_type"),
        "amount_min": amount_min,
        "amount_max": amount_max,
        "raw_data": raw_trade,
        "source_id": raw_trade.get("source", "S119")
    }

def normalize_insider_trade(raw_trade):
    return {
        "id": raw_trade.get("id"),
        "insider_name": raw_trade.get("insider_name"),
        "insider_title": raw_trade.get("insider_title"),
        "ticker": raw_trade.get("ticker", "").upper(),
        "transaction_date": raw_trade.get("transaction_date"),
        "filing_date": raw_trade.get("filing_date"),
        "transaction_type": raw_trade.get("transaction_type"),
        "shares": raw_trade.get("shares", 0),
        "price": raw_trade.get("price", 0.0),
        "value": raw_trade.get("value", 0.0),
        "raw_data": raw_trade,
        "source_id": raw_trade.get("source", "S028")
    }
