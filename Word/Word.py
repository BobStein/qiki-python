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
    :type content: six.string_types | Word | instancemethod

    :type sbj: Number | Word
    :type vrb: Number | instancemethod
    :type obj: Number | Word
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
            self._from_txt(content)
        elif isinstance(content, Number):
            self._from_id(content)
        elif isinstance(content, type(self)):
            pass
        elif isinstance(content, type(self.define)):   # instancemethod
            # TODO: look up a vrb by its txt field being content.__name__
            pass
        elif content is None:
            self.__id = None
            self.sbj = sbj
            self.vrb = vrb
            self.obj = obj
            self.num = num
            self.txt = txt
        else:
            typename = type(content).__name__
            if typename == 'instance':
                pass#typename = content.__class__.__name__
            raise TypeError('Word(%s) is not supported' % typename)

    @classmethod
    def connect(cls, connection_specs, table=None):
        # cls._connection = sqlite3.connect(database)
        assert table is not None
        cls._connection = mysql.connector.connect(**connection_specs)
        cls._table = table

    _ID_DEFINE = Number(1)
    _ID_NOUN   = Number(2)
    _ID_VERB   = Number(3)
    _ID_AGENT  = Number(4)
    _ID_SYSTEM = Number(5)

    @classmethod
    def install_from_scratch(cls):
        cls.uninstall()
        define = Word(
            sbj = cls._ID_SYSTEM,
            vrb = cls._ID_DEFINE,
            obj = cls._ID_VERB,
            num = Number(1),
            txt = u'define'
        )
        noun = Word(
            sbj = cls._ID_SYSTEM,
            vrb = cls._ID_DEFINE,
            obj = cls._ID_NOUN,
            num = Number(1),
            txt = u'noun'
        )
        verb = Word(
            sbj = cls._ID_SYSTEM,
            vrb = cls._ID_DEFINE,
            obj = cls._ID_NOUN,
            num = Number(1),
            txt = u'verb'
        )
        agent = Word(
            sbj = cls._ID_SYSTEM,
            vrb = cls._ID_DEFINE,
            obj = cls._ID_NOUN,
            num = Number(1),
            txt = u'agent'
        )
        system = Word(
            sbj = cls._ID_SYSTEM,
            vrb = cls._ID_DEFINE,
            obj = cls._ID_AGENT,
            num = Number(1),
            txt = u'system'
        )
        define.__id = cls._ID_DEFINE
        noun.__id = cls._ID_NOUN
        verb.__id = cls._ID_VERB
        agent.__id = cls._ID_AGENT
        system.__id = cls._ID_SYSTEM
        try:
            define.save()
            noun.save()
            verb.save()
            agent.save()
            system.save()
        except mysql.connector.IntegrityError:
            pass

    def __call__(self, *args, **kwargs):
        try:
            return self._as_if_method(*args, **kwargs)
        except:
            raise

    def define(self, obj, txt, meta_verb=None):
        word_object = Word(self, sbj=self, vrb=self.define, obj=obj, txt=txt)
        if meta_verb is not None:
            def verb_method(self, obj, txt, meta_verb=None):   # or something
                pass
            word_object._as_if_method = verb_method
        return word_object


    @classmethod
    def uninstall(cls):
        cursor = cls._connection.cursor(prepared=True)
        cursor.execute("DELETE FROM `{table}`".format(table=cls._table))
        cursor.close()

    @classmethod
    def disconnect(cls):
        cls._connection.close()

    def _from_id(self, id):
        assert isinstance(id, Number)
        self._loadrow(
            "SELECT * FROM `{table}` WHERE `id` = x'{id}'"
            .format(
                table=self._table,
                id=id.hex(),
            )
        )

    # TODO: _from_txt() should only be used on definitions, i.e. vrb = define.id
    def _from_txt(self, txt):
        assert isinstance(txt, six.string_types)
        self._loadrow(
            "SELECT * FROM `{table}` WHERE `txt` = ?"
            .format(
                table=self._table,
            ),
            (txt,)
        )

    def _loadrow(self, sql, params=()):
        cursor = self._connection.cursor(prepared=True)
        cursor.execute(sql, params)
        tuple_row = cursor.fetchone()
        dict_row = dict(zip(cursor.column_names, tuple_row))
        self.__id = Number.from_raw(six.binary_type(dict_row['id']))
        self.sbj = Number.from_raw(six.binary_type(dict_row['sbj']))
        self.vrb = Number.from_raw(six.binary_type(dict_row['vrb']))
        self.obj = Number.from_raw(six.binary_type(dict_row['obj']))
        self.txt = str(dict_row['txt'].decode('utf-8'))   # http://stackoverflow.com/q/27566078/673991
        cursor.close()


    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, value):
        raise RuntimeError("Cannot set a Word's id")

    def __repr__(self):
        return self.txt


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
