"""
qiki.py - Collection of qiki classes.

Usage example:

    from qiki import Number, Word

    one = Number(1)

Usage example:

    import qiki

    one = qiki.Number(1)
"""

from number import Number
from number import Suffix
from word import Word
from word import Lex
from word import LexSentence
from word import LexMemory
from word import LexMySQL
from word import Listing
from word import Qoolbar
from word import QoolbarSimple
from word import Text
__all__ = [
    'Number',
    'Word',
    'Lex',
    'LexSentence',
    'LexMemory',
    'LexMySQL',
    'Listing',
    'Qoolbar',
    'QoolbarSimple',
    'Text',
    'Suffix',
]
