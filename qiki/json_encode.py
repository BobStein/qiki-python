
import json


class JsonUniversalEncoderClass(json.JSONEncoder):
    """Custom converter for json_encode()."""

    def default(self, x):
        if hasattr(x, 'to_json') and callable(x.to_json):
            return x.to_json()
        else:
            return super(JsonUniversalEncoderClass, self).default(x)
            # NOTE:  Raises a TypeError, unless a multi-derived class
            #        calls a sibling class.  (If that's even how multiple
            #        inheritance works.)
            # NOTE:  This is not the same TypeError as the one that
            #        complains about custom dictionary keys.


JSON_SEPARATORS_NO_SPACES = (',', ':')


def json_encode(x, **kwargs):
    """ JSON encode custom objects with a .to_json() method. """
    json_almost = json.dumps(
        x,
        cls=JsonUniversalEncoderClass,
        separators=JSON_SEPARATORS_NO_SPACES,
        allow_nan=False,
        **kwargs
        # NOTE:  The output may have no newlines.  (Unless indent=4 is in kwargs.)
        #        If there APPEAR to be newlines when viewed in a browser Ctrl-U page source,
        #        it may just be the browser wrapping on the commas.
    )

    json_for_script = json_almost.replace('<', r'\u003C')
    # SEE:  (my answer) JSON for a script element, https://stackoverflow.com/a/57796324/673991
    # THANKS:  Jinja2 html safe json dumps utility, for inspiration
    #          https://github.com/pallets/jinja/blob/90595070ae0c8da489faf24f153b918d2879e759/jinja2/utils.py#L549

    return json_for_script
