def compute_signal(nikkei_ret, nyse_ret, w1=0.5, w2=0.5, threshold=0.003):
    raw = w1 * nikkei_ret + w2 * nyse_ret
    if abs(raw) < threshold:
        return "flat", raw
    return ("long" if raw > 0 else "short"), raw
