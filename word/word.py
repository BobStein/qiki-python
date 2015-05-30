"""
A qiki Word is defined by a three-word subject-verb-object
"""


import six
import time
import mysql.connector
from number import Number

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
        self.exists = False
        self.__id = None
        self._as_if_method = self.null_verb_method
        assert self._connection is not None, "Call Word.setup(database path)"
        if isinstance(content, six.string_types):
            self._from_definition(content)
        elif isinstance(content, Number):
            self._from_id(content)
        elif isinstance(content, type(self)):
            self._from_word(content)
        elif isinstance(content, type(self.define)):   # instancemethod
            # TODO: look up a vrb by its txt field being content.__name__
            pass
        elif content is None:
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
        assert table is not None
        cls._connection = mysql.connector.connect(**connection_specs)
        cls._table = table

    _ID_DEFINE = Number(1)
    _ID_NOUN   = Number(2)
    _ID_VERB   = Number(3)
    _ID_AGENT  = Number(4)
    _ID_SYSTEM = Number(5)

    _ID_MAX_FIXED = Number(5)

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
        return self._as_if_method(*args, **kwargs)

    def null_verb_method(*args, **kwargs):
        pass

    def noun(self, txt, num=Number(1)):
        return self.define(Word('noun'), txt, num)

    def define(self, obj, txt, num=Number(1), meta_verb=None):
        word_object = Word(sbj=self.id, vrb=Word('define').id, obj=obj.id, num=num, txt=txt)
        # if meta_verb is not None:
        #     def verb_method(_self, _obj, _txt, _meta_verb=None):   # or something
        #         # TODO: load fields and then self.save()
        #         pass
        #     word_object._as_if_method = verb_method
        word_object.save()
        return word_object

    @classmethod
    def uninstall(cls):
        cursor = cls._connection.cursor(prepared=True)
        cursor.execute("DELETE FROM `{table}`".format(table=cls._table))
        cursor.close()

    @classmethod
    def disconnect(cls):
        cls._connection.close()

    def _from_id(self, _id):
        """Construct a Word from its id
        :type _id: Number
        """
        assert isinstance(_id, Number)
        self._load_row(
            "SELECT * FROM `{table}` WHERE `id` = x'{id}'"
            .format(
                table=self._table,
                id=_id.hex(),
            )
        )

    def _from_definition(self, txt):
        """Construct a Word from its txt"""
        assert isinstance(txt, six.string_types)
        self._load_row(
            "SELECT * FROM `{table}` WHERE `vrb` = x'{define}' AND `txt` = ?"
            .format(
                table=self._table,
                define=self._ID_DEFINE.hex(),
            ),
            (txt,)
        )
        if not self.exists:
            self.txt = txt

    def _from_word(self, word):
        if word.exists:
            self._from_id(word.id)
        else:
            self._from_definition(word.txt)

    def _load_row(self, sql, params=()):
        cursor = self._connection.cursor(prepared=True)
        cursor.execute(sql, params)
        tuple_row = cursor.fetchone()
        if tuple_row is not None:
            self.exists = True
            dict_row = dict(zip(cursor.column_names, tuple_row))
            self.__id = self.number_from_mysql(dict_row['id'])
            self.sbj = self.number_from_mysql(dict_row['sbj'])
            self.vrb = self.number_from_mysql(dict_row['vrb'])
            self.obj = self.number_from_mysql(dict_row['obj'])
            self.num = self.number_from_mysql(dict_row['num'])
            self.txt = str(dict_row['txt'].decode('utf-8'))   # http://stackoverflow.com/q/27566078/673991
        cursor.close()

    def is_a(self, word):
        return self.vrb == self._ID_DEFINE and self.obj == word.id

    def description(self):
        sbj = Word(self.sbj)
        vrb = Word(self.vrb)
        obj = Word(self.obj)
        return "{sbj}.{vrb}({obj}, {txt}{maybe_num})".format(
            sbj=sbj.txt,
            vrb=vrb.txt,
            obj=obj.txt,
            txt=repr(self.txt),
            maybe_num=(", " + str(self.num)) if self.num != 1 else "",
        )

    @staticmethod
    def number_from_mysql(mysql_blob):
        return Number.from_raw(six.binary_type(mysql_blob))

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, value):
        raise RuntimeError("Cannot set a Word's id")

    def __repr__(self):
        if hasattr(self, 'txt'):
            return "Word('{0}')".format(self.txt)
        elif hasattr(self, '__id'):
            return "Word(Number('{id_qstring}'))".format(qstring=self.id.qstring())

    @classmethod
    def max_id(cls):
        cursor = cls._connection.cursor()
        cursor.execute("SELECT MAX(id) FROM `{table}`".format(table=cls._table))
        return cls.number_from_mysql(cursor.fetchone()[0])

    def save(self):
        assert isinstance(self.__id, (Number, type(None)))
        assert isinstance(self.sbj, Number)
        assert isinstance(self.vrb, Number)
        assert isinstance(self.obj, Number)
        assert isinstance(self.num, Number)
        assert isinstance(self.txt, six.string_types)
        assert not self.exists
        _id = self.__id
        if _id is None:
            _id = self.max_id().inc()   # AUTO sorta INCREMENT
        assert isinstance(_id, Number)
        cursor = self._connection.cursor(prepared=True)
        cursor.execute(
            "INSERT INTO `{table}` "
            "       (  `id`,    `sbj`,    `vrb`,    `obj`,    `num`, `txt`,   `whn`) "
            "VALUES (x'{id}', x'{sbj}', x'{vrb}', x'{obj}', x'{num}',    ?, x'{whn}')"
            .format(
                table=self._table,
                id=_id.hex(),
                sbj=self.sbj.hex(),
                vrb=self.vrb.hex(),
                obj=self.obj.hex(),
                num=self.num.hex(),
                whn=Number(time.time()).hex(),
            ),
            (self.txt, )
        )
        self._connection.commit()
        self.exists = True
        cursor.close()


# TODO: raise subclass of built-in exceptions
