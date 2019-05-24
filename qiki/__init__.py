"""
qiki - Collection of qiki classes.

Usage example:

    from qiki import Number, Word

    one = Number(1)

Usage example:

    import qiki

    one = qiki.Number(1)
"""

from qiki.number import Number
from qiki.number import Suffix
from qiki.word import Word
from qiki.word import Lex
from qiki.word import LexSentence
from qiki.word import LexMemory
from qiki.word import LexMySQL
from qiki.word import Listing
from qiki.word import Qoolbar
from qiki.word import QoolbarSimple
from qiki.word import Text

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
