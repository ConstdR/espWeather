import json
from espwconst import *

_hextobyte_cache = None

def unquote(string):
    """unquote('abc%20de+f') -> b'abc de f'."""
    global _hextobyte_cache

    # Note: strings are encoded as UTF-8. This is only an issue if it contains
    # unescaped non-ASCII characters, which URIs should not.
    if not string:
        return b''

    if isinstance(string, str):
        string = string.replace('+', ' ')
        string = string.encode('utf-8')

    bits = string.split(b'%')
    if len(bits) == 1:
        return string

    res = [bits[0]]
    append = res.append

    # Build cache for hex to char mapping on-the-fly only for codes
    # that are actually used
    if _hextobyte_cache is None:
        _hextobyte_cache = {}

    for item in bits[1:]:
        try:
            code = item[:2]
            char = _hextobyte_cache.get(code)
            if char is None:
                char = _hextobyte_cache[code] = bytes([int(code, 16)])
            append(char)
            append(item[2:])
        except KeyError:
            append(b'%')
            append(item)

    return b''.join(res)

def get_config():
    defcfg = {'essid':'essid', 'pswd':'pswd', 'tz':TZ,
              'longitude':ALT_LONGITUDE, 'message':'',
              'action':'az_mid', 'message':"No config"}
    try:
        fh = open(CFG_NAME, 'r')
        cfg = json.loads(fh.read())
        fh.close()
        cfg['tz'] = float(cfg.get('tz', TZ))
        cfg['longitude'] = float(cfg.get('longitude', ALT_LONGITUDE))
        cfg['message'] = 'Existing Config.'
        print("Existing Config: %s" % cfg)
        return cfg
    except Exception as e:
        print("Error getting config: %s" % e)
        return defcfg
