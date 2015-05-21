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
    :type sbj: Number
    :type vrb: Number
    :type obj: Number
    :type num: Number
    :type txt: six.string_types

    :type _ID_DEFINE: Number
    :type _connection: mysql.connector.ySQLConnection
    """
    _connection = None
    _table = None

    def __init__(self, content=None, sbj=None, vrb=None, obj=None, num=None, txt=None):
        assert self._connection is not None, "Call Word.setup(database path)"
        if isinstance(content, six.string_types):
            self._from_name(content)
        elif isinstance(content, type(self)):
            pass
        elif isinstance(content, type(self._define)):   # instancemethod
            # TODO: look up a vrb by its txt field being content.__name__
            pass
        elif content is None:
            self.__id = None
            self.sbj = sbj
            self.vrb = vrb
            self.obj = obj
            self.num = num
            self.txt = txt

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
            sbj = cls._ID_DEFINE,
            vrb = cls._ID_DEFINE,
            obj = cls._ID_VERB,
            num = Number(1),
            txt = u'define'
        )
        noun = Word(
            sbj = cls._ID_NOUN,
            vrb = cls._ID_DEFINE,
            obj = cls._ID_NOUN,
            num = Number(1),
            txt = u'noun'
        )
        verb = Word(
            sbj = cls._ID_VERB,
            vrb = cls._ID_DEFINE,
            obj = cls._ID_NOUN,
            num = Number(1),
            txt = u'verb'
        )
        define.__id = cls._ID_DEFINE
        noun.__id = cls._ID_NOUN
        verb.__id = cls._ID_VERB
        try:
            define.save()
            noun.save()
            verb.save()
        except mysql.connector.IntegrityError:
            pass

    def _define(self, obj, txt, vrb_def=None):
        if vrb_def is not None:
            def vrb_method(self, obj, txt, vrb_def=None):
                pass
            return vrb_method
        else:
            return Word(self, sbj=self, vrb=self._define, obj=obj, txt=txt)


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
            "SELECT * FROM `{table}` WHERE `txt` = ?"
            .format(
                table=self._table,
            ),
            (name,)
        )
        row = dict(zip(cursor.column_names, cursor.fetchone()))
        self.__id = row['id']
        self.sbj = row['sbj']
        self.vrb = row['vrb']
        self.obj = row['obj']
        cursor.close()


    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, value):
        raise RuntimeError("Cannot set a Word's id")




    def save(self):
        assert isinstance(self.__id,    Number)
        assert isinstance(self.sbj, Number)
        assert isinstance(self.vrb,    Number)
        assert isinstance(self.obj,  Number)
        assert isinstance(self.num,  Number)
        assert isinstance(self.txt, six.string_types)
        cursor = self._connection.cursor(prepared=True)
        cursor.execute(
            "INSERT INTO `{table}` "
            "       (  `id`,    `sbj`,    `vrb`,    `obj`,    `num`, `txt`,   `whn`) "
            "VALUES (x'{id}', x'{sbj}', x'{vrb}', x'{obj}', x'{num}',    ?, x'{whn}')"
            .format(
                table = self._table,
                id = self.__id.hex(),
                sbj = self.sbj.hex(),
                vrb = self.vrb.hex(),
                obj = self.obj.hex(),
                num = self.num.hex(),
                whn = Number(time.time()).hex(),
            ),
            (self.txt, )
        )
        self._connection.commit()
        cursor.close()
