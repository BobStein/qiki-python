"""
qiki - Rate and relate anything.

Usage example:

    import qiki

    one = qiki.Number(1)
    lex = qiki.LexMySQL(**credentials)
    like = lex.verb('like')
    mint = lex.noun('mint')
    kate = lex.define('agent', 'kate')   # create an agent named Kate.  Every sbj is an agent.
    kate(like)[mint] = one, "peppermint not spearmint"   # Kate likes mint x 1
    kate(like)['pistachio'] = 10                         # Kate likes pistachio x 10
    word = kate(like, num=1000, txt="Omg puppies!")      # Kate likes puppies x 1000
    assert isinstance(word, qiki.Word)

Usage example:

    from qiki import Number, Word, LexMySQL

    one = Number(1)
    lex = LexMySQL(**credentials)
"""

from .number import Number
from .number import Suffix
from .word import Word
from .word import Lex
from .word import LexSentence
from .word import LexInMemory
from .word import LexMySQL
from .word import Listing
from .word import Qoolbar
from .word import QoolbarSimple
from .word import Text
from .word import TimeLex

__all__ = [
    'Number',
    'Word',
    'Lex',
    'LexSentence',
    'LexInMemory',
    'LexMySQL',
    'Listing',
    'Qoolbar',
    'QoolbarSimple',
    'Text',
    'Suffix',
]

from . import version
__version__ = version.__doc__