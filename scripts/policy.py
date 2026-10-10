"""Conservative decisions for the undocumented Codex usage endpoint."""
def window(data):
    try:
        rate = data['rate_limit']
        primary = rate['primary_window']
        if primary['limit_window_seconds'] != 18000:
            return None
        return rate, primary
    except (KeyError, TypeError):
        return None

def decide(data, now, last):
    parsed = window(data)
    if not parsed:
        return 'unknown'
    rate, primary = parsed
    weekly = rate.get('secondary_window') or {}
    if weekly.get('used_percent', 0) >= 100 or rate.get('allowed') is False:
        return 'blocked'
    reset = primary.get('reset_at')
    if not isinstance(reset, (int, float)):
        return 'unknown'
    if last and now - last < 3600:
        return 'skip'
    if now < reset < now + 17880:
        return 'skip'
    return 'send'

def activated(before, after, started, now):
    parsed = window(after)
    old = window(before)
    if not parsed or not old:
        return False
    primary = parsed[1]
    reset = primary.get('reset_at')
    if not isinstance(reset, (int, float)) or not now < reset <= started + 18010:
        return False
    # An unstarted window slides forward at full length. A timer pinned near
    # request time must have measurably less than the full duration remaining.
    return now - started >= 15 and reset - now < 17990
