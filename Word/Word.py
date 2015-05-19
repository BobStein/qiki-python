"""
A qiki Word is defined by a three-word subject-verb-object
"""


import six
import time
# import sqlite3
import mysql.connector
from Number import Number

class Word(object):
    """
    :type __id: Number | None
    :type subject: Number
    :type verb: Number
    :type object: Number
    :type number: Number
    :type text: six.string_types

    :type _ID_DEFINE: Number
    :type _connection: mysql.connector.ySQLConnection
    """
    _connection = None
    _table = None

    def __init__(self, content=None, subject=None, verb=None, object=None, number=None, text=None):
        assert self._connection is not None, "Call Word.setup(database path)"
        if isinstance(content, six.string_types):
            self._from_name(content)
        elif content is None:
            self.__id = None
            self.subject = subject
            self.verb    = verb
            self.object  = object
            self.number  = number
            self.text    = text

    @classmethod
    def connect(cls, connection_specs, table=None):
        # cls._connection = sqlite3.connect(database)
        assert table is not None
        cls._connection = mysql.connector.connect(**connection_specs)
        cls._table = table

    _ID_DEFINE = Number(1)
    _ID_NOUN   = Number(2)
    _ID_VERB   = Number(3)

    @classmethod
    def install_from_scratch(cls):
        define = Word(
            subject=cls._ID_DEFINE,
            verb   =cls._ID_DEFINE,
            object =cls._ID_VERB,
            number=Number(1),
            text=u'define'
        )
        noun = Word(
            subject=cls._ID_NOUN,
            verb   =cls._ID_DEFINE,
            object =cls._ID_NOUN,
            number=Number(1),
            text=u'noun'
        )
        verb = Word(
            subject=cls._ID_VERB,
            verb   =cls._ID_DEFINE,
            object =cls._ID_NOUN,
            number=Number(1),
            text=u'verb'
        )
        define.__id = cls._ID_DEFINE
        noun  .__id = cls._ID_NOUN
        verb  .__id = cls._ID_VERB
        try:
            define.save()
            noun.save()
            verb.save()
        except mysql.connector.IntegrityError:
            pass

    @classmethod
    def uninstall(cls):
        pass
        # cls._connection.execute("DELETE * FROM `{table}`".format(table=cls._table))

    @classmethod
    def disconnect(cls):
        cls._connection.close()

    def _from_name(self, name):
        cursor = self._connection.cursor(prepared=True)
        cursor.execute(
            "SELECT * FROM `{table}` WHERE `text` = ?"
            .format(
                table=self._table,
            ),
            (name,)
        )
        row = dict(zip(cursor.column_names, cursor.fetchone()))
        self.__id = row['id']
        self.subject = row['subject']
        self.verb = row['verb']
        self.object = row['object']
        cursor.close()


    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, value):
        raise RuntimeError("Cannot set a Word's id")




    def save(self):
        assert isinstance(self.__id,    Number)
        assert isinstance(self.subject, Number)
        assert isinstance(self.verb,    Number)
        assert isinstance(self.object,  Number)
        assert isinstance(self.number,  Number)
        assert isinstance(self.text, six.string_types)
        cursor = self._connection.cursor(prepared=True)
        cursor.execute(
            "INSERT INTO `{table}` "
            "       (  `id`,    `subject`,    `verb`,    `object`,    `number`,`text`,   `when`) "
            "VALUES (x'{id}', x'{subject}', x'{verb}', x'{object}', x'{number}',    ?, x'{when}')"
            .format(
                table=self._table,
                id     =self.__id   .hex(),
                subject=self.subject.hex(),
                verb   =self.verb   .hex(),
                object =self.object .hex(),
                number =self.number .hex(),
                when=Number(time.time()).hex(),
            ),
            (self.text, )
        )
        self._connection.commit()
        cursor.close()
